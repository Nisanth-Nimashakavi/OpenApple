"""OpenApple Engine (Simple Edition): Dead-simple ledger tracking."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

LEDGER_PATH = Path.home() / ".openapple" / "ledger.json"


class OpenAppleEngine:
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or LEDGER_PATH
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        self.state: Dict[str, Any] = {"total_apples": 0, "history": []}
        self._load()

    def _load(self) -> None:
        if self.data_path.exists():
            try:
                self.state = json.loads(self.data_path.read_text(encoding="utf-8"))
                if "total_apples" not in self.state:
                    self.state["total_apples"] = 0
                if "history" not in self.state:
                    self.state["history"] = []
                return
            except Exception:
                pass
        self._persist()

    def _persist(self) -> None:
        self.data_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def register(self, task: str, approved: bool, agent: str = "Agent", note: str = "") -> Dict[str, Any]:
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M"),
            "agent": agent,
            "task": task,
            "approved": approved,
            "note": note,
        }
        if approved:
            self.state["total_apples"] += 1
        self.state["history"].append(entry)
        self._persist()
        return entry
