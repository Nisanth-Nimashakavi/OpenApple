"""Inspect actual release contents and import the wheel outside the checkout."""

import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from zipfile import ZipFile

root = Path(__file__).resolve().parent.parent
package = json.loads((root / "package.json").read_text())
version = package["version"]
wheel = root / "dist" / f"openapple-{version}-py3-none-any.whl"
archive = root / f"lordnimnim-openapple-{version}.tgz"
with ZipFile(wheel) as built:
    names = built.namelist()
    assert "openapple/backend.py" in names
    assert "openapple/audio.py" not in names, "Stale build directory included removed code"
    assert not any(name.endswith((".js", ".html")) for name in names), "Wheel is backend-only"
    assert any(name.endswith("LICENSE") for name in names)
    with tempfile.TemporaryDirectory(prefix="openapple-wheel-") as directory:
        built.extractall(directory)
        code = "import sys; sys.path.insert(0, sys.argv[1]); import openapple; from openapple.engine import OpenAppleEngine; assert openapple.__version__ == sys.argv[2]; print(openapple.__file__)"
        imported = subprocess.check_output(
            [sys.executable, "-I", "-c", code, directory, version], cwd=directory, text=True
        )
        assert directory in imported
with tarfile.open(archive) as built:
    names = built.getnames()
    required = [
        "main.js",
        "preload.js",
        "overlay.html",
        "overlay.js",
        "overlay.css",
        "desktop/backend.cjs",
        "desktop/runtime.cjs",
        "desktop/bridge.cjs",
        "desktop/delivery.cjs",
        "desktop/application.cjs",
        "desktop/feeding.cjs",
        "desktop/platforms.cjs",
        "desktop/native/macos.js",
        "desktop/native/windows.ps1",
        "desktop/reviews.cjs",
        "openapple/backend.py",
        "LICENSE",
        "pyproject.toml",
    ]
    assert all(f"package/{name}" in names for name in required)
    assert not any("node_modules" in name or ".egg-info" in name or "bridge.token" in name for name in names)
    with tempfile.TemporaryDirectory(prefix="openapple-npm-") as directory:
        if hasattr(tarfile, "data_filter"):
            built.extractall(directory, filter="data")
        else:
            assert all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in names)
            built.extractall(directory)
        env = {
            **os.environ,
            "OPENAPPLE_PYTHON": sys.executable,
            "OPENAPPLE_DATA_DIR": str(Path(directory) / "data"),
        }
        executable = Path(directory) / "package" / "bin" / "openapple.js"
        result = subprocess.check_output(
            ["node", str(executable), "--version"], cwd=directory, env=env, text=True
        )
        assert result.strip() == version
        assert not (Path(directory) / "data").exists(), "--version must not write user data"
print(f"Wheel and npm {version} contents and isolated entry points verified")
