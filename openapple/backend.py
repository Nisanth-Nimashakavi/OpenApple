"""Private JSON-lines backend for Electron. stdout is protocol-only."""

import json
import sys

from openapple.engine import OpenAppleEngine


def run() -> None:
    engine = OpenAppleEngine()
    for line in sys.stdin:
        envelope = {}
        try:
            if len(line) > 32768:
                raise ValueError("Message too large")
            envelope = json.loads(line)
            operation = envelope["operation"]
            arguments = envelope.get("arguments", {})
            if operation == "health":
                result = {"application": "openapple", "protocol": 1}
            elif operation == "snapshot":
                result = engine.state
            elif operation in {"create", "get", "decide", "pending", "delivery", "assign"}:
                result = getattr(engine, operation)(**arguments)
            else:
                raise ValueError("Unknown operation")
            response = {"id": envelope["id"], "result": result}
        except Exception as exc:
            response = {"id": envelope.get("id") if isinstance(envelope, dict) else None, "error": str(exc)}
        print(json.dumps(response), flush=True)


if __name__ == "__main__":
    run()
