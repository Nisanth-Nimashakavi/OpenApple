"""Scoped, validated configuration merges with backups and atomic replacement."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import stat
import sys
import tempfile
from collections.abc import MutableMapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import tomlkit


def get_agent_config_paths() -> dict[str, list[Path]]:
    home = Path.home()
    codex = Path(os.environ.get("CODEX_HOME", str(home / ".codex")))
    # Explicit overrides also make isolated testing and nonstandard installs possible.
    return {
        "claude": [Path(os.environ.get("OPENAPPLE_CLAUDE_CONFIG", str(home / ".claude.json")))],
        "agy": [
            Path(os.environ.get("OPENAPPLE_AGY_CONFIG", str(home / ".gemini" / "config" / "mcp_config.json")))
        ],
        "codex": [Path(os.environ.get("OPENAPPLE_CODEX_CONFIG", str(codex / "config.toml")))],
    }


def _registration() -> dict[str, Any]:
    entry: dict[str, Any] = {"command": sys.executable, "args": ["-m", "openapple.server"]}
    if os.environ.get("OPENAPPLE_DESKTOP_DIR"):
        entry["env"] = {"OPENAPPLE_DESKTOP_DIR": os.environ["OPENAPPLE_DESKTOP_DIR"]}
    return entry


def _atomic_write(path: Path, content: bytes) -> None:
    """Preserve the original before replacing; refuse concurrent/symlink writes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(f"Refusing to replace symlink {path}")
    previous = path.read_bytes() if path.exists() else None
    if previous == content:
        return
    if previous is not None:
        digest = hashlib.sha256(previous).hexdigest()[:12]
        backup = path.with_name(f"{path.name}.openapple-{digest}.bak")
        try:
            fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(previous)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            if backup.read_bytes() != previous:
                raise ValueError(f"Backup differs: {backup}")
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        if (path.read_bytes() if path.exists() else None) != previous:
            raise ValueError(f"Configuration changed during setup: {path}; retry")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _config_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".openapple.lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError(
            f"Setup already holds {lock}; if it crashed, inspect before removing the stale lock"
        ) from exc
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink()


def update_config(path: Path, *, dry_run: bool = False, remove: bool = False) -> None:
    if dry_run:
        _update_config(path, dry_run=True, remove=remove)
    else:
        with _config_lock(path):
            _update_config(path, remove=remove)


def _update_config(path: Path, *, dry_run: bool = False, remove: bool = False) -> None:
    if path.is_symlink():
        raise ValueError(f"Refusing to modify symlink {path}")
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    if remove and not original:
        return
    is_toml = path.suffix == ".toml"
    data = tomlkit.parse(original) if is_toml else json.loads(original) if original else {}
    key = "mcp_servers" if is_toml else "mcpServers"
    if not isinstance(data, MutableMapping):
        raise ValueError("Config root must be an object/table")
    if key in data and not isinstance(data[key], MutableMapping):
        raise ValueError(f"{key} must be an object/table; existing value preserved")
    if key not in data:
        data[key] = {}
    if remove:
        data[key].pop("openapple", None)
    else:
        # Preserve host-specific OpenApple options while repairing executable details.
        existing = data[key].get("openapple", {})
        if not isinstance(existing, MutableMapping):
            raise ValueError("Existing OpenApple registration must be an object/table")
        for field, value in _registration().items():
            if field == "env" and isinstance(existing.get("env"), MutableMapping):
                existing["env"].update(value)
            else:
                existing[field] = value
        data[key]["openapple"] = existing
    output = tomlkit.dumps(data) if is_toml else json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if is_toml:
        tomlkit.parse(output)
    else:
        json.loads(output)
    if dry_run:
        print(f"Would {'remove' if remove else 'register'} OpenApple: {path}")
    else:
        _atomic_write(path, output.encode())


def install_mcp_for_json(config_path: Path) -> bool:
    try:
        update_config(config_path)
        return True
    except (OSError, ValueError, tomlkit.exceptions.TOMLKitError) as exc:
        print(f"Cannot configure {config_path}: {exc}", file=sys.stderr)
        return False


def install_mcp_for_toml(config_path: Path) -> bool:
    return install_mcp_for_json(config_path)


def install_agents(target: str = "all", *, dry_run: bool = False, remove: bool = False) -> bool:
    paths = get_agent_config_paths()
    if target not in {*paths, "all"}:
        raise ValueError("Unknown agent target")
    if not remove:
        importlib.metadata.version("mcp")
    success = True
    for agent in paths if target == "all" else [target]:
        for path in paths[agent]:
            try:
                update_config(path, dry_run=dry_run, remove=remove)
                print(f"{agent}: {path}")
            except (OSError, ValueError, tomlkit.exceptions.TOMLKitError) as exc:
                success = False
                print(f"{agent}: {exc}", file=sys.stderr)
    return success


def run_doctor(*, json_output: bool = False) -> int:
    from openapple.gui import DesktopUnavailable, bridge_request

    checks: dict[str, Any] = {
        "Operating System": platform.platform(),
        "python": sys.executable,
        "node": shutil.which("node"),
        "keyboard_delivery": "MCP replies; direct terminal delivery unavailable",
    }
    if sys.platform == "darwin" and shutil.which("osascript"):
        checks["keyboard_delivery"] = (
            "macOS adapter; Accessibility/Automation permission and native validation required"
        )
    elif sys.platform == "win32" and shutil.which("powershell.exe"):
        checks["keyboard_delivery"] = (
            "Windows adapter; execution policy/input permission and native validation required"
        )
    elif os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
        checks["keyboard_delivery"] = (
            "Hyprland terminal delivery"
            if shutil.which("hyprctl") and shutil.which("wtype")
            else "Hyprland: install hyprctl and wtype; MCP replies available"
        )
    elif os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        checks["keyboard_delivery"] = (
            "X11 adapter; native validation required"
            if shutil.which("xdotool")
            else "X11: install xdotool; MCP replies available"
        )
    try:
        checks["mcp"] = importlib.metadata.version("mcp")
    except importlib.metadata.PackageNotFoundError:
        checks["mcp"] = None
    registrations = {}
    for agent, paths in get_agent_config_paths().items():
        path = paths[0]
        try:
            raw = path.read_text(encoding="utf-8")
            parsed = tomlkit.parse(raw) if path.suffix == ".toml" else json.loads(raw)
            entry = parsed.get("mcp_servers" if path.suffix == ".toml" else "mcpServers", {}).get("openapple")
            healthy = (
                isinstance(entry, MutableMapping)
                and entry.get("command") == sys.executable
                and entry.get("args") == ["-m", "openapple.server"]
            )
            registrations[agent] = "configured" if healthy else "not configured or stale"
        except FileNotFoundError:
            registrations[agent] = "not configured"
        except (OSError, ValueError, AttributeError, tomlkit.exceptions.TOMLKitError):
            registrations[agent] = "invalid config"
    checks["agents"] = registrations
    try:
        checks["desktop"] = (
            "ready"
            if bridge_request("GET", "/health") == {"application": "openapple", "protocol": 1}
            else "wrong protocol"
        )
    except DesktopUnavailable:
        checks["desktop"] = "not running"
    if json_output:
        print(json.dumps(checks, indent=2))
    else:
        print("OpenApple Environment Doctor")
        for key, value in checks.items():
            print(f"{key}: {value}")
    return 0 if checks["mcp"] and checks["node"] and checks["desktop"] == "ready" else 1
