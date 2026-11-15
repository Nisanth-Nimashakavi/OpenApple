"""Clean npm bootstrap check. Downloads dependencies into an isolated runtime."""

import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parent.parent
version = json.loads((root / "package.json").read_text())["version"]
with tempfile.TemporaryDirectory(prefix="openapple-install-") as temporary:
    work = Path(temporary)
    with tarfile.open(root / f"lordnimnim-openapple-{version}.tgz") as archive:
        archive.extractall(work, filter="data") if hasattr(tarfile, "data_filter") else archive.extractall(
            work
        )
    env = {
        **os.environ,
        "OPENAPPLE_DATA_DIR": str(work / "data"),
        "OPENAPPLE_PYTHON": sys.executable,
        "OPENAPPLE_CODEX_CONFIG": str(work / "configs" / "codex.toml"),
        "OPENAPPLE_CLAUDE_CONFIG": str(work / "configs" / "claude.json"),
        "OPENAPPLE_AGY_CONFIG": str(work / "configs" / "agy.json"),
        "PIP_CACHE_DIR": str(work / "pip-cache"),
        "OPENAPPLE_HEADLESS": "1",
    }
    launcher = work / "package" / "bin" / "openapple.js"
    setup = subprocess.run(
        ["node", str(launcher), "setup", "codex"],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if setup.returncode:
        raise RuntimeError(setup.stdout + setup.stderr)
    python = (
        work
        / "data"
        / "runtime"
        / ("Scripts" if os.name == "nt" else "bin")
        / ("python.exe" if os.name == "nt" else "python")
    )
    check = subprocess.run(
        [str(python), "-m", "openapple.cli", "--version"], cwd=work, env=env, capture_output=True, text=True
    )
    assert check.returncode == 0 and check.stdout.strip() == version, check.stderr
    import tomlkit

    config = tomlkit.parse((work / "configs" / "codex.toml").read_text())
    assert config["mcp_servers"]["openapple"]["command"] == str(python)
    assert not (work / "configs" / "claude.json").exists()
    assert not (work / "configs" / "agy.json").exists()
    status = subprocess.run(
        [str(python), "-m", "openapple.cli", "status"], cwd=work, env=env, capture_output=True, text=True
    )
    assert status.returncode == 0, status.stderr
    assert json.loads(status.stdout)["total_apples"] == 0
    print(
        "Packed npm setup: isolated Python bootstrap, selected-target registration, installed CLI and empty orchard verified outside checkout."
    )
