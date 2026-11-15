"""Every test gets private data and host config paths before application access."""

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAPPLE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("OPENAPPLE_SOUND", "0")
    monkeypatch.setenv("OPENAPPLE_HEADLESS", "1")
    for agent, suffix in [("CLAUDE", "json"), ("AGY", "json"), ("CODEX", "toml")]:
        monkeypatch.setenv(f"OPENAPPLE_{agent}_CONFIG", str(tmp_path / f"{agent}.{suffix}"))
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
