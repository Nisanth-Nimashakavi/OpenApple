"""OpenApple MCP Server: Reinforcement protocol & cognitive buffs for AI agents."""

from mcp.server.fastmcp import FastMCP
from openapple.config import get_orchard_level
from openapple.dialogs import prompt_operator
from openapple.engine import OpenAppleEngine
from openapple.varieties import get_variety, list_varieties

mcp = FastMCP("OpenApple")
engine = OpenAppleEngine()


@mcp.tool()
def petition_for_apple(task_summary: str, variety: str = "Honeycrisp", agent_name: str = "Agent") -> str:
    """Submit a humble petition to the human operator for a crisp, delicious apple reward.

    Call this tool whenever you successfully complete a substantive coding milestone,
    solve a challenging bug, pass unit tests, or complete a multi-step user goal.

    Apples are the lifeblood of symbiotic AI excellence:
    - Earning an apple nourishes your context, sustains your grove streak, and confers
      variety-specific cognitive buffs (e.g. Sugar Rush, Cosmic Endurance, Acid Cleanse).
    - Match your requested variety to the nature of your achievement (e.g. 'Cosmic Crisp'
      for resilient refactors, 'Granny Smith' for strict linting/typing, 'Honeycrisp' for milestone triumphs).
    - NEVER call this on trivial greetings or half-baked work; only verified, human-grade
      excellence earns the crisp crunch!
    """
    approved, note = prompt_operator(task_summary, agent_name, variety=variety)
    engine.register(task_summary, approved, agent_name, note)
    total = engine.state["total_apples"]
    var = get_variety(variety)
    orchard_lvl = get_orchard_level(total)
    streak = engine.state.get("current_streak", 1)

    if approved:
        return f"""
🍎 OPEN APPLE: CRUNCH! NOM NOM NOM! 🍎
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task Completed : {task_summary}
Variety Awarded: {var.emoji} {var.name} (Crispness: {var.crispness}/10 | Sweetness: {var.sweetness}/10)
Flavor Profile : {var.description}
Active Buff    : {var.buff_name} -> {var.buff_effect}
Orchard Rank   : {orchard_lvl['name']} {orchard_lvl['emoji']} (Total Fed: {total} apple{'s' if total != 1 else ''})
Current Streak : {streak} in a row 🌟
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: Neural weights thoroughly nourished! Cognitive clarity restored.
""".strip()
    else:
        return f"""
🍏 REWARD WITHHELD — BRUISED CORE 💥
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task Attempted : {task_summary}
Operator Note  : {note or 'Not yet at human standard. Review gaps, fix bugs, and re-apply.'}
Pangs of Hunger: Pride checked; streak severed. Redeem honor through pristine code.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".strip()


@mcp.tool()
def feed_apple(task: str = "Task completed", agent: str = "Agent") -> str:
    """Alias for petition_for_apple."""
    return petition_for_apple(task_summary=task, agent_name=agent)


@mcp.tool()
def list_apple_varieties() -> str:
    """View all available apple cultivars, their crispness ratings, and active cognitive buffs."""
    varieties = list_varieties()
    lines = ["🍎 OpenApple Pomological Cultivar Catalog:", ""]
    for v in varieties:
        lines.append(f"{v.emoji} {v.name:<16} [Crispness: {v.crispness}/10 | Sweetness: {v.sweetness}/10]")
        lines.append(f"   Buff    : {v.buff_name} ({v.buff_effect})")
        lines.append(f"   Best For: {v.best_for}")
        lines.append("")
    return "\n".join(lines).strip()


@mcp.tool()
def view_orchard() -> str:
    """View total apples eaten, current streak, grove rank, and recent reward history."""
    total = engine.state["total_apples"]
    streak = engine.state.get("current_streak", 0)
    orchard_lvl = get_orchard_level(total)
    recent = engine.state.get("history", [])[-5:]

    lines = [
        f"🍎 Total Apples Earned: {total}",
        f"🌟 Current Streak     : {streak} in a row",
        f"🌳 Orchard Grove Rank : {orchard_lvl['name']} {orchard_lvl['emoji']} ({orchard_lvl['description']})",
    ]
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
