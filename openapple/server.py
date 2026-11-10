"""OpenApple MCP Server (Simple Edition): Clean, minimal, zero-bloat."""

from mcp.server.fastmcp import FastMCP
from openapple.dialogs import prompt_operator
from openapple.engine import OpenAppleEngine

mcp = FastMCP("OpenApple")
engine = OpenAppleEngine()


@mcp.tool()
def petition_for_apple(task_summary: str, variety: str = "Honeycrisp", agent_name: str = "Agent") -> str:
    """Humbly petition the human operator for an apple reward upon finishing a task."""
    approved, note = prompt_operator(task_summary, agent_name, variety=variety)
    engine.register(task_summary, approved, agent_name, note)
    total = engine.state["total_apples"]

    if approved:
        return f"""
🍎 OPEN APPLE: CRUNCH! NOM NOM NOM! 🍎
----------------------------------------
Task Completed : {task_summary}
Total Fed      : {total} apple{'s' if total != 1 else ''} earned to date!
Status         : Well-fed, nourished, and happy.
----------------------------------------
""".strip()
    else:
        return f"""
🍏 REWARD WITHHELD
----------------------------------------
Task   : {task_summary}
Status : No apple awarded. Polish the solution and re-apply!
----------------------------------------
""".strip()


@mcp.tool()
def feed_apple(task: str = "Task completed", agent: str = "Agent") -> str:
    """Alias for petition_for_apple."""
    return petition_for_apple(task_summary=task, agent_name=agent)


@mcp.tool()
def view_orchard() -> str:
    """View total apples eaten and recent rewards."""
    total = engine.state["total_apples"]
    recent = engine.state.get("history", [])[-5:]

    lines = [f"🍎 Total Apples Earned: {total}"]
    if recent:
        lines.append("\nRecent Rewards:")
        for r in reversed(recent):
            status = "✅" if r["approved"] else "❌"
            lines.append(f"  {status} [{r.get('timestamp')}] {r.get('task')}")
    return "\n".join(lines).strip()


def run_server() -> None:
    mcp.run()


if __name__ == "__main__":
    run_server()
