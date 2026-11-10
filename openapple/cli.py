"""OpenApple CLI: Fast, Smooth & Fun reward tool for AI agents (Claude, AGY, Codex)."""

import argparse
import sys
from openapple.audio import play_sound
from openapple.engine import OpenAppleEngine
from openapple.gui import launch_gui
from openapple.installer import install_agents, run_doctor


def main():
    parser = argparse.ArgumentParser(prog="openapple", description="OpenApple: Smooth positive reinforcement for Claude, AGY, and Codex.")
    subparsers = parser.add_subparsers(dest="command")

    # feed
    p_feed = subparsers.add_parser("feed", help="Feed an apple with crunch sound & overlay")
    p_feed.add_argument("task", nargs="?", default="Good job on the task!", help="Task summary")
    p_feed.add_argument("--agent", "-a", default="", help="Target agent: claude, agy, or codex (auto-detected if omitted)")
    p_feed.add_argument("--variety", "-v", default="Honeycrisp", help="Apple variety (e.g. Honeycrisp, Cosmic Crisp, Fuji)")

    # install
    p_inst = subparsers.add_parser("install", help="Configure AI agents (Claude, AGY, Codex)")
    p_inst.add_argument("target", nargs="?", default="all", choices=["all", "claude", "agy", "codex"], help="Target agent ecosystem")

    # doctor
    subparsers.add_parser("doctor", help="Check OS compatibility, audio, keyboard injection & agents")

    # status, overlay, serve
    subparsers.add_parser("status", help="Show total apples earned")
    subparsers.add_parser("overlay", help="Spawn the smooth cursor apple overlay")
    subparsers.add_parser("gui", help="Alias for overlay")
    subparsers.add_parser("button", help="Alias for overlay")
    subparsers.add_parser("serve", help="Run the MCP server")

    args = parser.parse_args()
    engine = OpenAppleEngine()

    if not args.command:
        # Running bare 'openapple' launches the smooth overlay, just like OpenWhip!
        print("🍎 Spawning OpenApple overlay... Click to feed!")
        launch_gui(engine)
        return

    if args.command == "status":
        total = engine.state.get("total_apples", 0)
        streak = engine.state.get("current_streak", 0)
        print(f"\n🍎 OpenApple Status")
        print(f"   Total Fed  : {total} apple{'s' if total != 1 else ''}")
        print(f"   Streak     : {streak} in a row 🌟")
        recent = engine.state.get("history", [])[-5:]
        if recent:
            print("\n   Recent Rewards:")
            for r in reversed(recent):
                status = "✅" if r.get("approved") else "❌"
                agent_tag = f"[{r.get('agent', 'agent').upper()}]"
                task_txt = r.get("task", "")[:50]
                print(f"     {status} {agent_tag} {task_txt}")
        print()

    elif args.command == "feed":
        task = args.task or "Good job on the task!"
        agent = getattr(args, "agent", "") or "claude"
        variety = getattr(args, "variety", "Honeycrisp")
        engine.register(task, True, agent, "CLI feed")
        play_sound("crunch")
        launch_gui(engine, task=task, variety=variety, agent=agent)
        total = engine.state.get("total_apples", 0)
        print(f"\n🍎 CRUNCH! Nom nom nom! Apple fed to {agent.upper()} for: \"{task}\" (Total: {total})\n")

    elif args.command == "install":
        install_agents(getattr(args, "target", "all"))

    elif args.command == "doctor":
        run_doctor()

    elif args.command in ("overlay", "gui", "button"):
        launch_gui(engine)

    elif args.command == "serve":
        from openapple.server import run_server
        run_server()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
