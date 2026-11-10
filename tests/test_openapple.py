"""Comprehensive test suite for OpenApple."""

from unittest.mock import patch
from openapple.config import get_orchard_level
from openapple.engine import OpenAppleEngine
from openapple.installer import (
    get_agent_config_paths,
    install_mcp_for_json,
    install_mcp_for_toml,
    run_doctor,
)
from openapple.server import petition_for_apple, view_orchard


def test_engine_register(tmp_path):
    ledger = tmp_path / "ledger.json"
    engine = OpenAppleEngine(data_path=ledger)
    assert engine.state["total_apples"] == 0

    engine.register("Fixed bug", True)
    assert engine.state["total_apples"] == 1

    engine.register("Bad code", False)
    assert engine.state["total_apples"] == 1
    assert len(engine.state["history"]) == 2


def test_server_tools():
    with patch("openapple.server.prompt_operator", return_value=(True, "Approved")):
        res = petition_for_apple("Wrote tests")
        assert "OPEN APPLE: CRUNCH!" in res
        assert "Total Fed" in res

    orchard = view_orchard()
    assert "Total Apples Earned" in orchard


def test_orchard_level_progression():
    lvl0 = get_orchard_level(0)
    assert lvl0["name"] == "Barren Soil"

    lvl5 = get_orchard_level(5)
    assert lvl5["name"] == "Sprouting Seedling"

    lvl100 = get_orchard_level(150)
    assert lvl100["name"] == "Ancient Grove"


def test_cross_platform_agent_config(tmp_path):
    paths = get_agent_config_paths()
    assert "claude" in paths
    assert "agy" in paths
    assert "codex" in paths

    # Test JSON config updater
    json_path = tmp_path / "test_mcp.json"
    assert install_mcp_for_json(json_path) is True
    content = json_path.read_text()
    assert "openapple-server" in content

    # Test TOML config updater
    toml_path = tmp_path / "config.toml"
    assert install_mcp_for_toml(toml_path) is True
    toml_content = toml_path.read_text()
    assert "[mcp_servers.openapple]" in toml_content
    assert 'command = "openapple-server"' in toml_content


def test_doctor_runs_cleanly(capsys):
    run_doctor()
    captured = capsys.readouterr()
    assert "OpenApple Environment Doctor" in captured.out
    assert "Operating System" in captured.out
