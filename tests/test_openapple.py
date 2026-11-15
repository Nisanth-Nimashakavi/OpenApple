"""Behavioral regressions for approvals, durability and non-destructive setup."""

import json
import os
import subprocess
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from unittest.mock import AsyncMock, patch

import anyio
import pytest
import tomlkit

from openapple.config import get_orchard_level
from openapple.engine import LedgerError, OpenAppleEngine
from openapple.gui import DesktopUnavailable, launch_gui
from openapple.installer import install_agents, run_doctor, update_config
from openapple.server import petition_for_apple


def _award(path, request_id):
    engine = OpenAppleEngine(Path(path))
    request = engine.create("Concurrent reward", request_id=request_id)
    return engine.decide(request["id"], "approved")["state"]


def test_pending_is_not_an_award(tmp_path):
    engine = OpenAppleEngine(tmp_path / "db.sqlite3")
    row = engine.create("Fixed a bug", variety="Fuji", agent="codex")
    assert engine.state["total_apples"] == 0
    assert row["state"] == "pending"
    result = engine.decide(row["id"], "approved", "Verified")
    assert result["variety"] == "Fuji"
    assert result["timestamp"].endswith("+00:00")
    assert engine.state["total_apples"] == 1
    assert engine.state["current_streak"] == 1
    assert engine.decide(row["id"], "approved")["id"] == row["id"]
    assert engine.state["total_apples"] == 1
    with pytest.raises(LedgerError):
        engine.decide(row["id"], "rejected")


@pytest.mark.parametrize("outcome", ["rejected", "cancelled"])
def test_nonapproval_never_awards(tmp_path, outcome):
    engine = OpenAppleEngine(tmp_path / "db.sqlite3")
    engine.decide(engine.create("Review this")["id"], outcome)
    assert engine.state["total_apples"] == 0


def test_stats_follow_decision_order_not_submission_order(tmp_path):
    engine = OpenAppleEngine(tmp_path / "db.sqlite3")
    old = engine.create("Old pending")
    new = engine.create("Newer petition")
    engine.decide(new["id"], "rejected")
    engine.decide(old["id"], "approved")
    engine.decide(engine.create("Drop this")["id"], "cancelled")
    assert engine.state["current_streak"] == 1
    engine.decide(engine.create("Needs work")["id"], "rejected")
    assert engine.state["current_streak"] == 0


def test_two_instances_and_processes_do_not_lose_or_duplicate_updates(tmp_path):
    path = str(tmp_path / "db.sqlite3")
    first, second = OpenAppleEngine(Path(path)), OpenAppleEngine(Path(path))
    first.decide(first.create("A")["id"], "approved")
    second.decide(second.create("B")["id"], "approved")
    assert first.state["total_apples"] == 2
    ids = [str(uuid.uuid4()) for _ in range(10)]
    with ProcessPoolExecutor(max_workers=4) as pool:
        assert list(pool.map(_award, [path] * 20, ids * 2)) == ["approved"] * 20
    assert second.state["total_apples"] == 12
    assert len(second.state["history"]) == 12


def test_retry_identity_and_expiry(tmp_path):
    engine = OpenAppleEngine(tmp_path / "db.sqlite3")
    row = engine.create("Original", ttl=1)
    assert engine.create("Original", request_id=row["id"])["id"] == row["id"]
    with pytest.raises(LedgerError):
        engine.create("Different", request_id=row["id"])
    with patch("openapple.engine.time.time", return_value=time.time() + 2):
        assert engine.decide(row["id"], "approved")["state"] == "expired"
    assert engine.state["total_apples"] == 0


@pytest.mark.parametrize("value", ["", "x" * 4001, None, "bad\x1btext"])
def test_request_validation(tmp_path, value):
    with pytest.raises(LedgerError):
        OpenAppleEngine(tmp_path / "db.sqlite3").create(value)


def test_bounded_queue_and_history(tmp_path):
    engine = OpenAppleEngine(tmp_path / "db.sqlite3")
    for _ in range(32):
        engine.create("Waiting")
    with pytest.raises(LedgerError, match="full"):
        engine.create("Overflow")


def test_valid_legacy_import_is_idempotent_and_preserves_original(tmp_path):
    path = tmp_path / "ledger.json"
    raw = json.dumps(
        {
            "total_apples": 1,
            "history": [{"task": "Old work", "approved": True, "timestamp": "2026-11-01 10:00"}],
        }
    ).encode()
    path.write_bytes(raw)
    assert OpenAppleEngine(path).state["total_apples"] == 1
    assert OpenAppleEngine(path).state["total_apples"] == 1
    assert path.read_bytes() == path.with_suffix(".json.pre-sqlite.bak").read_bytes() == raw


@pytest.mark.parametrize("raw", ["{broken", '{"total_apples": 10, "history": []}', '{"history": "bad"}'])
def test_invalid_legacy_is_preserved(tmp_path, raw):
    path = tmp_path / "ledger.json"
    path.write_text(raw)
    with pytest.raises(LedgerError):
        OpenAppleEngine(path)
    assert path.read_text() == raw


def test_import_has_no_filesystem_side_effect(tmp_path):
    result = subprocess.run(
        [sys.executable, "-c", "import openapple.server"], capture_output=True, env=os.environ
    )
    assert result.returncode == 0, result.stderr.decode()
    assert not Path(os.environ["OPENAPPLE_DATA_DIR"]).exists()


def test_unavailable_review_does_not_read_stdin_or_award():
    with (
        patch("openapple.gui.ensure_tray_running", side_effect=DesktopUnavailable("headless")),
        patch("builtins.input", side_effect=AssertionError("MCP must not read stdin")),
    ):
        result = anyio.run(petition_for_apple, "Work")
    assert "no approval confirmed" in result
    assert not Path(os.environ["OPENAPPLE_DATA_DIR"]).exists()


def test_server_returns_committed_result_without_registering_again():
    result = {"state": "approved", "agent": "codex", "task": "Work", "variety": "Fuji", "id": "receipt"}
    with patch("openapple.server.prompt_operator", new=AsyncMock(return_value=result)):
        assert "Fuji" in anyio.run(petition_for_apple, "Work")
    assert not Path(os.environ["OPENAPPLE_DATA_DIR"]).exists()


def test_cold_start_preserves_metadata_and_waits_for_decision():
    request = {"id": "receipt", "state": "pending"}
    with (
        patch("openapple.gui.ensure_tray_running", return_value=True),
        patch(
            "openapple.gui.bridge_request", side_effect=[request, {**request, "state": "approved"}]
        ) as bridge,
        patch("openapple.gui.time.sleep"),
    ):
        assert launch_gui("Work", "Fuji", "codex", wait=True)["state"] == "approved"
    submitted = bridge.call_args_list[0].args[2]
    assert (submitted["task"], submitted["variety"], submitted["agent"]) == ("Work", "Fuji", "codex")


@pytest.mark.parametrize(
    "suffix, raw", [("json", "{broken"), ("json", "[]"), ("json", '{"mcpServers": []}'), ("toml", "[broken")]
)
def test_bad_config_is_never_replaced(tmp_path, suffix, raw):
    path = tmp_path / f"config.{suffix}"
    path.write_text(raw)
    with pytest.raises((ValueError, tomlkit.exceptions.TOMLKitError)):
        update_config(path)
    assert path.read_text() == raw
    assert not list(tmp_path.glob("*.bak"))


@pytest.mark.parametrize("suffix", ["json", "toml"])
def test_merge_repair_backup_and_uninstall(tmp_path, suffix):
    path = tmp_path / f"config.{suffix}"
    original = (
        '{"theme":"dark","mcpServers":{"other":{"command":"keep"}}}'
        if suffix == "json"
        else '# [mcp_servers.openapple] old example\ntheme = "dark"\n[mcp_servers.other]\ncommand = "keep"\n'
    )
    path.write_text(original)
    update_config(path)
    first = path.read_text()
    update_config(path)
    assert path.read_text() == first
    data = json.loads(first) if suffix == "json" else tomlkit.parse(first)
    key = "mcpServers" if suffix == "json" else "mcp_servers"
    assert data["theme"] == "dark"
    assert data[key]["other"]["command"] == "keep"
    assert data[key]["openapple"]["command"] == sys.executable
    assert any(p.read_text() == original for p in tmp_path.glob("*.bak"))
    if suffix == "toml":
        assert "# [mcp_servers.openapple] old example" in first
    update_config(path, remove=True)
    after = json.loads(path.read_text()) if suffix == "json" else tomlkit.parse(path.read_text())
    assert "openapple" not in after[key] and "other" in after[key]


def test_dry_run_and_selected_target(tmp_path, capsys):
    assert install_agents("codex", dry_run=True)
    assert not list(tmp_path.glob("*.toml"))
    assert install_agents("codex")
    assert (tmp_path / "CODEX.toml").is_file()
    assert not (tmp_path / "CLAUDE.json").exists()
    assert not (tmp_path / "AGY.json").exists()


def test_atomic_failure_keeps_original(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"keep":true}')
    with patch("openapple.installer.os.replace", side_effect=OSError("disk failure")), pytest.raises(OSError):
        update_config(path)
    assert path.read_text() == '{"keep":true}'


def test_doctor_is_read_only_and_honest(capsys):
    assert run_doctor(json_output=True) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["desktop"] == "not running"
    assert all(value == "not configured" for value in report["agents"].values())
    assert not Path(os.environ["OPENAPPLE_DATA_DIR"]).exists()


@pytest.mark.parametrize(
    "count,name", [(0, "Barren Soil"), (5, "Sprouting Seedling"), (100, "Ancient Grove")]
)
def test_rank_boundaries(count, name):
    assert get_orchard_level(count)["name"] == name


def test_equal_timestamps_use_transactional_decision_order(tmp_path):
    engine = OpenAppleEngine(tmp_path / "db.sqlite3")
    rows = [engine.create(str(i)) for i in range(3)]
    with patch("openapple.engine.time.time", return_value=1000000):
        for row, decision in zip(rows, ["approved", "rejected", "approved"]):
            engine.decide(row["id"], decision)
    state = engine.state
    assert state["current_streak"] == 1
    assert [row["state"] for row in state["history"]] == ["approved", "rejected", "approved"]


def test_mcp_cancellation_cancels_desktop_receipt():
    from openapple.gui import await_review

    calls = []

    def bridge(method, route, payload=None):
        calls.append((method, route))
        return {"state": "pending"}

    async def exercise():
        with anyio.fail_after(5):
            async with anyio.create_task_group() as tasks:
                tasks.start_soon(await_review, "Work", "codex", "Fuji")
                while not calls:
                    await anyio.sleep(0.01)
                tasks.cancel_scope.cancel()

    with (
        patch("openapple.gui.ensure_tray_running", return_value=True),
        patch("openapple.gui.bridge_request", side_effect=bridge),
    ):
        anyio.run(exercise)
    assert calls[-1][0] == "POST" and calls[-1][1].endswith("/cancel")


def test_lost_submit_response_attempts_cancel_and_reports_receipt():
    with (
        patch("openapple.gui.ensure_tray_running", return_value=True),
        patch(
            "openapple.gui.bridge_request", side_effect=[DesktopUnavailable("Lost response"), {}]
        ) as bridge,
    ):
        with pytest.raises(DesktopUnavailable, match="receipt"):
            launch_gui("Work", wait=True)
    assert bridge.call_args.args[1].endswith("/cancel")


@pytest.mark.parametrize("command", [["--help"], ["--version"], ["status"]])
def test_legacy_editable_launcher_can_run_core_commands_without_site_packages(command):
    result = subprocess.run(
        [sys.executable, "-S", "-m", "openapple.cli", *command],
        cwd=Path(__file__).resolve().parents[1],
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr


def test_missing_setup_dependency_reports_exact_interpreter_repair():
    result = subprocess.run(
        [sys.executable, "-S", "-m", "openapple.cli", "doctor", "--json"],
        cwd=Path(__file__).resolve().parents[1],
        env=dict(os.environ),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "tomlkit>=0.13,<1" in result.stderr
    assert sys.executable in result.stderr
    assert "pip install" in result.stderr
    assert not result.stdout


def test_migration_accepts_mixed_historical_schemas(tmp_path):
    path = tmp_path / "ledger.json"
    history = [
        {
            "task_summary": "Oldest format",
            "agent": "codex",
            "variety": "Fuji",
            "operator_feedback": "Verified",
            "timestamp": 1760000000.125,
            "approved": True,
        },
        {"task": "Python format", "timestamp": "2026-11-01 10:00", "approved": False, "note": "Needs work"},
        {"task": "Desktop format", "timestamp": "2026-11-02T10:00:00.000Z", "approved": True},
    ]
    original = json.dumps({"total_apples": 2, "history": history}).encode()
    path.write_bytes(original)
    state = OpenAppleEngine(path).state
    assert state["total_apples"] == 2
    assert len(state["history"]) == 3
    assert state["history"][0]["task"] == "Oldest format"
    assert state["history"][0]["note"] == "Verified"
    assert state["history"][0]["variety"] == "Fuji"
    assert state["history"][0]["created"] == 1760000000.125
    assert state["current_streak"] == 1
    assert path.read_bytes() == original
    assert path.with_suffix(".json.pre-sqlite.bak").read_bytes() == original
    assert OpenAppleEngine(path).state["total_apples"] == 2


def test_historical_text_is_not_subject_to_new_submission_rules(tmp_path):
    path = tmp_path / "ledger.json"
    tasks = ["", " padded task ", "x" * 4001]
    path.write_text(
        json.dumps(
            {
                "total_apples": 3,
                "history": [
                    {"task_summary": task, "timestamp": 1760000000 + index, "approved": True}
                    for index, task in enumerate(tasks)
                ],
            }
        )
    )
    engine = OpenAppleEngine(path)
    assert [row["task"] for row in engine.state["history"]] == tasks
    with pytest.raises(LedgerError):
        engine.create("")


@pytest.mark.parametrize("stamp", [None, True, float("nan"), float("inf"), "invalid"])
def test_unsupported_legacy_dates_preserve_data_and_identify_row(tmp_path, stamp):
    path = tmp_path / "ledger.json"
    original = json.dumps(
        {"total_apples": 1, "history": [{"task_summary": "Work", "timestamp": stamp, "approved": True}]}
    )
    path.write_text(original)
    with pytest.raises(LedgerError, match="entry 1"):
        OpenAppleEngine(path)
    assert path.read_text() == original


def test_manual_feed_records_named_recipient_and_delivery_once(tmp_path):
    engine = OpenAppleEngine(tmp_path / "db.sqlite3")
    row = engine.create("Good work", source="client")
    row = engine.assign(row["id"], "Codex", "Codex · OpenApple conversation")
    assert row["agent"] == "Codex"
    assert row["recipient"] == "Codex · OpenApple conversation"
    assert engine.create("Good work", source="client", request_id=row["id"])["id"] == row["id"]
    with pytest.raises(LedgerError):
        engine.delivery(row["id"], "sent")
    engine.decide(row["id"], "approved")
    engine.delivery(row["id"], "sending")
    result = engine.delivery(row["id"], "sent")
    assert result["delivery_status"] == "sent"
    assert engine.delivery(row["id"], "sent")["id"] == row["id"]
    with pytest.raises(LedgerError):
        engine.delivery(row["id"], "sending")
    assert engine.state["total_apples"] == 1


def test_mcp_receipt_stays_bound_to_the_requesting_chat(tmp_path):
    engine = OpenAppleEngine(tmp_path / "db.sqlite3")
    row = engine.create("Finished feature", source="mcp", agent="Claude")
    with pytest.raises(LedgerError):
        engine.assign(row["id"], "Codex", "A different chat")
    engine.decide(row["id"], "approved")
    assert engine.delivery(row["id"], "mcp")["agent"] == "Claude"


def test_approved_mcp_apple_asks_its_recipient_for_a_chat_reaction():
    result = {
        "state": "approved",
        "agent": "Codex",
        "task": "Good work",
        "variety": "Fuji",
        "id": "receipt",
        "note": "Beautiful fix",
    }
    with patch("openapple.server.prompt_operator", new=AsyncMock(return_value=result)):
        response = anyio.run(petition_for_apple, "Good work", "Fuji", "Codex")
    assert "for YOU, Codex" in response
    assert "React to the apple in your next message in this conversation" in response
    assert "Fuji" in response and "Beautiful fix" in response
    assert "do not petition again" in response
