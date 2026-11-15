"""Authenticated desktop client. A successful launch is never an approval."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from openapple.engine import data_directory


class DesktopUnavailable(RuntimeError):
    """The desktop cannot complete a human review."""


def _port() -> int:
    port = int(os.environ.get("OPENAPPLE_PORT", "52199"))
    if not 1024 <= port <= 65535:
        raise DesktopUnavailable("OPENAPPLE_PORT must be between 1024 and 65535")
    return port


def bridge_request(method: str, route: str, payload: dict[str, Any] | None = None) -> Any:
    try:
        token = (data_directory() / "bridge.token").read_text(encoding="utf-8").strip()
        if len(token) != 64:
            raise DesktopUnavailable("Invalid bridge credentials")
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            f"http://127.0.0.1:{_port()}{route}",
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        # Ignore proxy variables for this private loopback protocol.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=3) as response:
            return json.loads(response.read(65536))
    except urllib.error.HTTPError as exc:
        detail = exc.read(8192).decode(errors="replace")
        raise DesktopUnavailable(f"Desktop rejected request ({exc.code}): {detail}") from exc
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise DesktopUnavailable(f"Desktop connection unavailable: {exc}") from exc


def desktop_root() -> Path:
    configured = os.environ.get("OPENAPPLE_DESKTOP_DIR")
    candidates = [Path(configured)] if configured else []
    candidates.append(Path(__file__).resolve().parent.parent)
    locator = data_directory() / "desktop.json"
    if locator.exists():
        try:
            candidates.append(Path(json.loads(locator.read_text())["root"]))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise DesktopUnavailable(f"Invalid desktop locator {locator}: {exc}") from exc
    for candidate in candidates:
        if (candidate / "main.js").is_file() and (candidate / "bin" / "openapple.js").is_file():
            return candidate.resolve()
    raise DesktopUnavailable(
        "Desktop not installed. Run npm install -g @lordnimnim/openapple, then openapple setup"
    )


def ensure_tray_running() -> bool:
    try:
        if bridge_request("GET", "/health") == {"application": "openapple", "protocol": 1}:
            return True
    except DesktopUnavailable:
        pass
    if os.environ.get("OPENAPPLE_HEADLESS") == "1":
        raise DesktopUnavailable("Desktop auto-start disabled in headless mode")
    if not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or sys.platform in {"darwin", "win32"}
    ):
        raise DesktopUnavailable("Human review requires the OpenApple desktop; no display is available")
    node = shutil.which("node")
    if not node:
        raise DesktopUnavailable("Node.js is required to start the desktop")
    root = desktop_root()
    log_dir = data_directory()
    log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (log_dir / "desktop.log").open("ab") as log:
        child = subprocess.Popen(
            [node, str(root / "bin" / "openapple.js"), "--tray-only"],
            cwd=root,
            stdout=log,
            stderr=log,
            start_new_session=os.name != "nt",
            env={**os.environ, "OPENAPPLE_PYTHON": sys.executable},
        )
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        try:
            if bridge_request("GET", "/health") == {"application": "openapple", "protocol": 1}:
                return True
        except DesktopUnavailable:
            pass
        if child.poll() not in (None, 0):
            break
        time.sleep(0.1)
    raise DesktopUnavailable(f"Desktop did not become ready; inspect {log_dir / 'desktop.log'}")


def launch_gui(
    task: str = "Good job!",
    variety: str = "Honeycrisp",
    agent: str = "Agent",
    wait: bool = False,
    timeout: int = 300,
) -> dict[str, Any]:
    if type(timeout) is not int or not 1 <= timeout <= 600:
        raise ValueError("timeout must be between 1 and 600 seconds")
    ensure_tray_running()
    request_id = str(uuid.uuid4())
    request: dict[str, Any] = {"state": "pending"}
    delivered = False
    deadline = time.monotonic() + timeout + 3
    try:
        request = bridge_request(
            "POST",
            "/petitions",
            {
                "request_id": request_id,
                "task": task,
                "agent": agent,
                "variety": variety,
                "ttl": timeout,
                "source": "client",
            },
        )
        delivered = True
        if not wait:
            return request
        while request["state"] == "pending" and time.monotonic() < deadline:
            time.sleep(0.2)
            request = bridge_request("GET", f"/petitions/{request_id}")
        if request["state"] == "pending":
            raise DesktopUnavailable("Human review timed out")
        return request
    except DesktopUnavailable as exc:
        raise DesktopUnavailable(f"{exc}; receipt {request_id}. Check orchard before retrying") from exc
    finally:
        # Cancellation is permitted to clients; approval is only private desktop IPC.
        if request["state"] == "pending" and (wait or not delivered):
            try:
                bridge_request("POST", f"/petitions/{request_id}/cancel", {})
            except DesktopUnavailable:
                pass


async def await_review(task: str, agent: str, variety: str) -> dict[str, Any]:
    """Cancellation-aware MCP review; the transport never waits on terminal input."""
    import anyio

    await anyio.to_thread.run_sync(ensure_tray_running)
    request_id = str(uuid.uuid4())
    row: dict[str, Any] = {"state": "pending"}
    try:
        # Complete submission before cancellation so its receipt can be cancelled reliably.
        with anyio.CancelScope(shield=True):
            row = await anyio.to_thread.run_sync(
                lambda: bridge_request(
                    "POST",
                    "/petitions",
                    {
                        "request_id": request_id,
                        "task": task,
                        "agent": agent,
                        "variety": variety,
                        "ttl": 300,
                        "source": "mcp",
                    },
                )
            )
        with anyio.fail_after(303):
            while row["state"] == "pending":
                await anyio.sleep(0.2)
                row = await anyio.to_thread.run_sync(
                    lambda: bridge_request("GET", f"/petitions/{request_id}")
                )
        if row["state"] == "approved":
            try:
                row = await anyio.to_thread.run_sync(
                    lambda: bridge_request("POST", f"/petitions/{request_id}/received", {})
                )
            except DesktopUnavailable:
                pass  # The approval is already committed; delivery metadata must not hide it.
        return row
    except (DesktopUnavailable, TimeoutError) as exc:
        raise DesktopUnavailable(f"{exc}; receipt {request_id}. Check orchard before retrying") from exc
    finally:
        if row["state"] == "pending":
            with anyio.CancelScope(shield=True):
                try:
                    await anyio.to_thread.run_sync(
                        lambda: bridge_request("POST", f"/petitions/{request_id}/cancel", {})
                    )
                except DesktopUnavailable:
                    pass
