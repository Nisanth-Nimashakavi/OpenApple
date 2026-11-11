"""Smooth OpenApple Overlay launcher (Hardware-accelerated Electron across Linux, macOS, and Windows)."""

import os
import platform
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from openapple.engine import OpenAppleEngine


def _get_popen_kwargs(cwd: str):
    """Return platform-safe subprocess kwargs for background execution."""
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "cwd": cwd,
    }
    if os.name == "nt":
        # Windows: CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
        kwargs["creationflags"] = 0x08000000 | 0x00000200
    else:
        kwargs["start_new_session"] = True
    return kwargs


def launch_gui(engine: OpenAppleEngine = None, task: str = "Good job!", variety: str = "Honeycrisp", agent: str = "claude"):
    """Launch or trigger the silky-smooth OpenApple overlay."""
    # 1. Check if the Electron app is already running and listening on localhost bridge
    try:
        url = f"http://127.0.0.1:52199/feed?task={urllib.parse.quote(task)}&variety={urllib.parse.quote(variety)}&agent={urllib.parse.quote(agent)}"
        req = urllib.request.Request(url, headers={"User-Agent": "OpenApple-CLI"})
        with urllib.request.urlopen(req, timeout=0.6) as resp:
            if resp.status == 200:
                return
    except Exception:
        pass

    # 2. Launch the Electron app via node & bin/openapple.js
    app_root = Path(__file__).resolve().parent.parent
    bin_js = app_root / "bin" / "openapple.js"
    node_bin = shutil.which("node")

    if bin_js.exists() and node_bin:
        try:
            subprocess.Popen([node_bin, str(bin_js)], **_get_popen_kwargs(str(app_root)))
            return
        except Exception:
            pass

    # 3. Direct Electron binary fallbacks across platforms
    sys_name = platform.system()
    candidate_paths = []

    # Check local node_modules
    local_dist = app_root / "node_modules" / "electron" / "dist"
    if sys_name == "Darwin":
        candidate_paths.append(local_dist / "Electron.app" / "Contents" / "MacOS" / "Electron")
    elif sys_name == "Windows":
        candidate_paths.append(local_dist / "electron.exe")
        candidate_paths.append(app_root / "node_modules" / ".bin" / "electron.cmd")
    else:
        candidate_paths.append(local_dist / "electron")
        candidate_paths.append(app_root / "node_modules" / ".bin" / "electron")

    # Global electron binaries
    generic_electron = shutil.which("electron") or shutil.which("electron.cmd")
    if generic_electron:
        candidate_paths.insert(0, Path(generic_electron))

    for ep in candidate_paths:
        if ep and ep.exists():
            try:
                subprocess.Popen([str(ep), str(app_root)], **_get_popen_kwargs(str(app_root)))
                return
            except Exception:
                pass


def ensure_tray_running() -> bool:
    """Ensure OpenApple desktop tray is running silently in background."""
    # 1. Quick probe localhost bridge
    try:
        url = "http://127.0.0.1:52199/status"
        req = urllib.request.Request(url, headers={"User-Agent": "OpenApple-CLI"})
        with urllib.request.urlopen(req, timeout=0.3) as resp:
            if resp.status == 200:
                return True
    except Exception:
        pass

    # Don't try in headless environments without display
    has_display = bool(
        os.environ.get("DISPLAY")
        or os.environ.get("WAYLAND_DISPLAY")
        or sys.platform in ("darwin", "win32")
    )
    if not has_display:
        return False

    app_root = Path(__file__).resolve().parent.parent
    bin_js = app_root / "bin" / "openapple.js"
    node_bin = shutil.which("node")

    # Try launching via bin/openapple.js --tray-only
    if bin_js.exists() and node_bin:
        try:
            subprocess.Popen([node_bin, str(bin_js), "--tray-only"], **_get_popen_kwargs(str(app_root)))
            return True
        except Exception:
            pass

    # Try global openapple binary
    global_openapple = shutil.which("openapple")
    if global_openapple:
        try:
            subprocess.Popen([global_openapple, "--tray-only"], **_get_popen_kwargs(str(app_root)))
            return True
        except Exception:
            pass

    return False


if __name__ == "__main__":
    launch_gui()
