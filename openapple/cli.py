"""Human-facing CLI. The desktop package owns the `openapple` command."""

import argparse
import json
import shlex
import sqlite3
import subprocess
import sys

from openapple import __version__
from openapple.engine import LedgerError, OpenAppleEngine
from openapple.gui import DesktopUnavailable, launch_gui


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="openapple", description="Human-reviewed apple rewards for AI agents"
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")
    feed = sub.add_parser("feed", help="Submit work and wait for human review")
    feed.add_argument("task", nargs="?", default="Good job on the task!")
    feed.add_argument("--agent", "-a", default="Agent")
    feed.add_argument("--variety", "-v", default="Honeycrisp")
    feed.add_argument("--timeout", type=int, default=300)
    for command in ("setup", "install", "uninstall"):
        setup = sub.add_parser(command, help=f"{command.title()} selected agent integrations")
        setup.add_argument("target", nargs="?", default="all", choices=["all", "claude", "agy", "codex"])
        setup.add_argument("--dry-run", action="store_true")
    doctor = sub.add_parser("doctor", help="Inspect runtime and registration health")
    doctor.add_argument("--json", action="store_true")
    sub.add_parser("status", help="Show committed orchard history")
    for command in ("overlay", "gui", "button"):
        sub.add_parser(command, help="Open a manual review request")
    sub.add_parser("serve", help="Run the stdio MCP adapter")
    args = parser.parse_args()
    try:
        if args.command in ("setup", "install", "uninstall"):
            from openapple.installer import install_agents

            return (
                0
                if install_agents(args.target, dry_run=args.dry_run, remove=args.command == "uninstall")
                else 1
            )
        if args.command == "doctor":
            from openapple.installer import run_doctor

            return run_doctor(json_output=args.json)
        if args.command == "serve":
            from openapple.server import run_server

            run_server()
        elif args.command == "status":
            print(json.dumps(OpenAppleEngine().state, indent=2, ensure_ascii=False))
        elif args.command == "feed":
            result = launch_gui(
                task=args.task, agent=args.agent, variety=args.variety, wait=True, timeout=args.timeout
            )
            print(f"Review {result['state']}: {result['task']} ({result['id']})")
            return 0 if result["state"] == "approved" else 2
        else:
            result = launch_gui()
            print(f"Review queued: {result['id']}")
        return 0
    except ModuleNotFoundError as exc:
        requirements = {
            "tomlkit": "tomlkit>=0.13,<1",
            "mcp": "mcp>=1.30,<2",
            "anyio": "anyio>=4.6,<5",
        }
        dependency = (exc.name or "").split(".")[0]
        if dependency not in requirements:
            raise
        repair = [sys.executable, "-m", "pip", "install", requirements[dependency]]
        command = subprocess.list2cmdline(repair) if sys.platform == "win32" else shlex.join(repair)
        print(
            f"OpenApple: runtime dependency unavailable ({exc.name}).\n"
            f"Repair the Python environment used by this launcher:\n  {command}",
            file=sys.stderr,
        )
        return 1
    except (OSError, LedgerError, DesktopUnavailable, sqlite3.Error, ValueError) as exc:
        print(f"OpenApple: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
