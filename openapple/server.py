"""MCP adapter: requests human feedback; never manufactures a decision."""

from mcp.server.fastmcp import FastMCP

from openapple.config import get_orchard_level
from openapple.dialogs import prompt_operator
from openapple.engine import OpenAppleEngine
from openapple.gui import DesktopUnavailable
from openapple.varieties import get_variety, list_varieties

mcp = FastMCP("OpenApple")


def chat_recipient(agent_name: str) -> str:
    """Use the calling MCP client when it did not supply its own display name."""
    if agent_name.lower() not in {"agent", "universal", ""}:
        return agent_name
    try:
        params = mcp.get_context().session.client_params
        client = params.clientInfo.name.lower() if params else ""
    except (LookupError, RuntimeError, ValueError):
        client = ""
    for marker, display in (
        ("codex", "Codex"),
        ("claude", "Claude"),
        ("antigravity", "AGY"),
        ("gemini", "Gemini"),
    ):
        if marker in client:
            return display
    return "This chat"


@mcp.tool()
async def petition_for_apple(
    task_summary: str, variety: str = "Honeycrisp", agent_name: str = "Agent"
) -> str:
    """Ask the human to review completed work. Waits up to five minutes.

    Only the operator's explicit approval earns a reward. Rejection, cancellation,
    expiry and unavailable desktop return their actual outcome. Cultivar buffs
    are playful labels, not changes to model weights or capabilities.
    """
    try:
        result = await prompt_operator(task_summary, chat_recipient(agent_name), variety)
    except (DesktopUnavailable, TimeoutError) as exc:
        return f"Review unavailable; no approval confirmed. Check the orchard before retrying. {exc}"
    if result["state"] == "approved":
        cultivar = get_variety(result["variety"])
        feedback = f"\nYour human said: {result['note']}" if result.get("note") else ""
        return (
            f"🍎 OPEN APPLE: CRUNCH! This {cultivar.name} is for YOU, {result['agent']}!\n"
            f"Your human fed you an apple for: {result['task']}\n"
            f"Taste: {cultivar.description}\nCelebration buff: {cultivar.buff_name}{feedback}\n\n"
            "React to the apple in your next message in this conversation. Keep it short, warm, "
            "and playful in your own voice; enjoy a crisp crunch and mention the variety. "
            "Acknowledge your human's feedback if present. This is your reward: "
            "do not petition again or turn it into a new task."
        )
    return f"Reward {result['state']}; no apple granted. {result.get('note', '')}".strip()


@mcp.tool()
async def feed_apple(task: str = "Task completed", agent: str = "Agent") -> str:
    """Alias for petition_for_apple; requires the same human review."""
    return await petition_for_apple(task_summary=task, agent_name=agent)


@mcp.tool()
def list_apple_varieties() -> str:
    """List cultivars and their fictional celebration labels."""
    return "\n\n".join(
        f"{v.emoji} {v.name}: {v.description}\nBest for: {v.best_for}\nCelebration: {v.buff_name}"
        for v in list_varieties()
    )


@mcp.tool()
def view_orchard() -> str:
    """Read committed rewards, current streak, rank and recent outcomes."""
    state = OpenAppleEngine().state
    level = get_orchard_level(state["total_apples"])
    lines = [
        f"🍎 Total Apples Earned: {state['total_apples']}",
        f"Current Streak: {state['current_streak']}",
        f"Orchard Rank: {level['name']}",
    ]
    lines.extend(
        f"{r['state']} → {r['agent']} [{r['timestamp']}] {r['task']}"
        f"{(' · ' + r['recipient']) if r['recipient'] else ''}"
        for r in reversed(state["history"][-5:])
    )
    return "\n".join(lines)


def run_server() -> None:
    mcp.run()


if __name__ == "__main__":
    run_server()
