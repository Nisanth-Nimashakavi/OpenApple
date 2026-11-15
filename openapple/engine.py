"""Transactional request lifecycle and reward history shared by all adapters."""

from __future__ import annotations

import json
import math
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

TERMINAL_STATES = frozenset({"approved", "rejected", "cancelled", "expired"})


class LedgerError(ValueError):
    """Invalid stored data or request transition; originals are preserved."""


def data_directory() -> Path:
    return Path(os.environ.get("OPENAPPLE_DATA_DIR", str(Path.home() / ".openapple")))


def text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise LedgerError(f"{field} must be nonempty text of at most {limit} characters")
    if any(ord(c) < 32 and c not in "\n\t" for c in value):
        raise LedgerError(f"{field} contains control characters")
    return value.strip()


def legacy_text(row: dict[str, Any], field: str, *aliases: str, default: str | None = None) -> str:
    """Read historical strings without applying new-request length/whitespace rules."""
    for key in (field, *aliases):
        value = row.get(key)
        if value is not None:
            if not isinstance(value, str):
                raise LedgerError(f"Legacy {key} must be text")
            return value
    if default is not None:
        return default
    raise LedgerError(f"Legacy record is missing {field}")


def legacy_timestamp(row: dict[str, Any]) -> float:
    stamp = row.get("timestamp")
    if stamp is None:
        stamp = row.get("datetime_iso")
    if isinstance(stamp, (int, float)) and not isinstance(stamp, bool) and math.isfinite(stamp):
        # Validate epoch range while preserving fractional seconds.
        return datetime.fromtimestamp(stamp, timezone.utc).timestamp()
    if isinstance(stamp, str):
        return datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    raise LedgerError("Legacy timestamp must be an ISO date or a finite epoch number")


class OpenAppleEngine:
    """Short-lived connections keep independent MCP/desktop processes consistent."""

    def __init__(self, data_path: Path | None = None):
        requested = Path(data_path) if data_path else data_directory() / "orchard.sqlite3"
        self.legacy_path = requested if requested.suffix == ".json" else requested.with_name("ledger.json")
        self.data_path = requested.with_suffix(".sqlite3") if requested.suffix == ".json" else requested
        self.data_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.data_path.is_symlink():
            raise LedgerError("Database must be a regular file, not a symlink")
        try:
            descriptor = os.open(self.data_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        except FileExistsError:
            pass
        with self._connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, 2, 3):
                raise LedgerError(f"Unsupported database schema {version}; upgrade OpenApple")
            db.execute("""CREATE TABLE IF NOT EXISTS requests (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
                task TEXT NOT NULL, agent TEXT NOT NULL, variety TEXT NOT NULL,
                source TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('pending','approved','rejected','cancelled','expired')),
                note TEXT NOT NULL DEFAULT '', decided REAL, decision_order INTEGER,
                recipient TEXT NOT NULL DEFAULT '', delivery_status TEXT NOT NULL DEFAULT 'none'
            )""")
            db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            if version == 1:
                db.execute("ALTER TABLE requests ADD COLUMN decision_order INTEGER")
                rows = db.execute(
                    "SELECT id FROM requests WHERE state!='pending' ORDER BY decided,seq"
                ).fetchall()
                for index, row in enumerate(rows, 1):
                    db.execute("UPDATE requests SET decision_order=? WHERE id=?", (index, row["id"]))
            if version in (1, 2):
                db.execute("ALTER TABLE requests ADD COLUMN recipient TEXT NOT NULL DEFAULT ''")
                db.execute("ALTER TABLE requests ADD COLUMN delivery_status TEXT NOT NULL DEFAULT 'none'")
            db.execute("PRAGMA user_version=3")
            self._import_legacy(db)
        if os.name != "nt":
            self.data_path.chmod(0o600)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.data_path, timeout=10, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=10000")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _import_legacy(self, db: sqlite3.Connection) -> None:
        if db.execute("SELECT 1 FROM metadata WHERE key='legacy_import'").fetchone():
            return
        if not self.legacy_path.exists():
            db.execute("INSERT INTO metadata VALUES ('legacy_import','absent')")
            return
        try:
            raw = self.legacy_path.read_bytes()
            data = json.loads(raw)
            if not isinstance(data, dict) or not isinstance(data.get("history"), list):
                raise LedgerError("Legacy ledger must contain a history array")
            total, history = data.get("total_apples"), data["history"]
            if type(total) is not int or total < 0:
                raise LedgerError("Legacy total_apples must be a nonnegative integer")
            if any(not isinstance(r, dict) or type(r.get("approved")) is not bool for r in history):
                raise LedgerError("Legacy history contains invalid decisions")
            if sum(r["approved"] for r in history) != total:
                raise LedgerError("Legacy totals disagree with history; reconcile a copy before migration")
            for index, row in enumerate(history):
                try:
                    task = legacy_text(row, "task", "task_summary")
                    agent = legacy_text(row, "agent", default="Agent")
                    variety = legacy_text(row, "variety", default="Honeycrisp")
                    note = legacy_text(row, "note", "operator_feedback", default="")
                    created = legacy_timestamp(row)
                except (ValueError, TypeError, OverflowError, OSError) as exc:
                    raise LedgerError(f"Legacy history entry {index + 1}: {exc}") from exc
                db.execute(
                    """INSERT INTO requests
                    (id,task,agent,variety,source,created,expires,state,note,decided,decision_order)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        f"legacy-{index}",
                        task,
                        agent,
                        variety,
                        "legacy",
                        created,
                        created,
                        "approved" if row["approved"] else "rejected",
                        note,
                        created,
                        index + 1,
                    ),
                )
            if self.legacy_path.read_bytes() != raw:
                raise LedgerError(
                    "Legacy ledger changed during migration; stop older OpenApple processes and retry"
                )
            backup = self.legacy_path.with_suffix(".json.pre-sqlite.bak")
            if backup.exists() and backup.read_bytes() != raw:
                raise LedgerError(f"Existing migration backup differs: {backup}")
            if not backup.exists():
                with backup.open("xb") as out:
                    out.write(raw)
                if os.name != "nt":
                    backup.chmod(0o600)
            db.execute("INSERT INTO metadata VALUES ('legacy_import','complete')")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise LedgerError(f"Cannot import {self.legacy_path}; original preserved: {exc}") from exc

    @staticmethod
    def _expire(db: sqlite3.Connection) -> None:
        now = time.time()
        order = db.execute("SELECT coalesce(max(decision_order),0) FROM requests").fetchone()[0]
        for row in db.execute(
            "SELECT id FROM requests WHERE state='pending' AND expires<=? ORDER BY seq", (now,)
        ).fetchall():
            order += 1
            db.execute(
                "UPDATE requests SET state='expired',decided=?,decision_order=? WHERE id=?",
                (now, order, row["id"]),
            )

    @staticmethod
    def _record(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["approved"] = result["state"] == "approved"
        result["timestamp"] = datetime.fromtimestamp(
            result["decided"] or result["created"], timezone.utc
        ).isoformat()
        return result

    def create(
        self,
        task: str,
        agent: str = "Agent",
        variety: str = "Honeycrisp",
        request_id: str | None = None,
        ttl: int = 300,
        source: str = "desktop",
        recipient: str = "",
    ) -> dict[str, Any]:
        task, agent, variety = (
            text(task, "task", 4000),
            text(agent, "agent", 80),
            text(variety, "variety", 80),
        )
        source = text(source, "source", 40)
        if not isinstance(recipient, str) or len(recipient) > 1000:
            raise LedgerError("recipient must be text of at most 1000 characters")
        if type(ttl) is not int or not 1 <= ttl <= 600:
            raise LedgerError("ttl must be an integer between 1 and 600 seconds")
        request_id = str(uuid.uuid4()) if request_id is None else request_id
        try:
            request_id = str(uuid.UUID(request_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise LedgerError("request_id must be a UUID") from exc
        with self._connection() as db:
            self._expire(db)
            existing = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
            if existing:
                # A human can attach a generic CLI request to a named chat before approval.
                if source == "client" and existing["recipient"]:
                    if agent.lower() == "agent":
                        agent = existing["agent"]
                    if not recipient:
                        recipient = existing["recipient"]
                if (
                    existing["task"],
                    existing["agent"],
                    existing["variety"],
                    existing["source"],
                    existing["recipient"],
                ) != (
                    task,
                    agent,
                    variety,
                    source,
                    recipient,
                ):
                    raise LedgerError("request_id already belongs to a different petition")
                return self._record(existing)
            if db.execute("SELECT count(*) FROM requests WHERE state='pending'").fetchone()[0] >= 32:
                raise LedgerError("Review queue is full; wait for the operator")
            now = time.time()
            db.execute(
                """INSERT INTO requests (id,task,agent,variety,source,created,expires,state,recipient)
                VALUES (?,?,?,?,?,?,?,'pending',?)""",
                (request_id, task, agent, variety, source, now, now + ttl, recipient),
            )
            return self._record(db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone())

    def get(self, request_id: str) -> dict[str, Any]:
        with self._connection() as db:
            self._expire(db)
            row = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
            if row is None:
                raise LedgerError("Unknown petition")
            return self._record(row)

    def assign(self, request_id: str, agent: str, recipient: str) -> dict[str, Any]:
        agent = text(agent, "agent", 80)
        recipient = text(recipient, "recipient", 1000)
        with self._connection() as db:
            self._expire(db)
            row = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
            if row is None or row["state"] != "pending" or row["source"] == "mcp":
                raise LedgerError("Only a pending manual feed can choose a chat")
            if row["source"] != "desktop" and row["agent"].lower() not in {
                "agent",
                "this chat",
                agent.lower(),
            }:
                raise LedgerError(f"This apple was requested for {row['agent']}; choose that agent's chat")
            db.execute("UPDATE requests SET agent=?,recipient=? WHERE id=?", (agent, recipient, request_id))
            return self._record(db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone())

    def decide(self, request_id: str, outcome: str, note: str = "") -> dict[str, Any]:
        if outcome not in TERMINAL_STATES - {"expired"}:
            raise LedgerError("Decision must be approved, rejected, or cancelled")
        if not isinstance(note, str) or len(note) > 2000:
            raise LedgerError("Note must be text of at most 2000 characters")
        with self._connection() as db:
            self._expire(db)
            row = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
            if row is None:
                raise LedgerError("Unknown petition")
            if row["state"] == "pending":
                db.execute(
                    "UPDATE requests SET state=?,note=?,decided=?,decision_order=? WHERE id=?",
                    (
                        outcome,
                        note,
                        time.time(),
                        db.execute("SELECT coalesce(max(decision_order),0)+1 FROM requests").fetchone()[0],
                        request_id,
                    ),
                )
            elif row["state"] != outcome and row["state"] != "expired":
                raise LedgerError("A terminal decision cannot be changed")
            return self._record(db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone())

    def pending(self) -> list[dict[str, Any]]:
        with self._connection() as db:
            self._expire(db)
            return [
                self._record(r)
                for r in db.execute("SELECT * FROM requests WHERE state='pending' ORDER BY seq")
            ]

    def delivery(self, request_id: str, status: str) -> dict[str, Any]:
        """Record delivery independently of the operator's award decision."""
        if status not in {"sending", "sent", "failed", "mcp"}:
            raise LedgerError("Invalid delivery status")
        with self._connection() as db:
            row = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
            if row is None or row["state"] != "approved":
                raise LedgerError("Only approved apples can be delivered")
            if row["delivery_status"] == status:
                return self._record(row)
            allowed = {"none": {"sending", "mcp"}, "sending": {"sent", "failed"}}
            if status not in allowed.get(row["delivery_status"], set()):
                raise LedgerError("This apple's delivery has already been handled")
            if status == "mcp" and row["source"] != "mcp":
                raise LedgerError("Only the requesting MCP chat can acknowledge this receipt")
            db.execute("UPDATE requests SET delivery_status=? WHERE id=?", (status, request_id))
            return self._record(db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone())

    @property
    def state(self) -> dict[str, Any]:
        """Fresh snapshot; only the most recent 100 events are materialized."""
        with self._connection() as db:
            self._expire(db)
            total = db.execute("SELECT count(*) FROM requests WHERE state='approved'").fetchone()[0]
            last_rejection = db.execute(
                "SELECT coalesce(max(decision_order),0) FROM requests WHERE state='rejected'"
            ).fetchone()[0]
            streak = db.execute(
                "SELECT count(*) FROM requests WHERE state='approved' AND decision_order>?", (last_rejection,)
            ).fetchone()[0]
            rows = db.execute(
                "SELECT * FROM requests WHERE state!='pending' ORDER BY decision_order DESC LIMIT 100"
            ).fetchall()
            return {
                "total_apples": total,
                "current_streak": streak,
                "history": [self._record(r) for r in reversed(rows)],
            }
