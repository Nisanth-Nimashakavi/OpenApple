"""Human review without reading or writing MCP transport streams."""

from typing import Any

from openapple.gui import await_review


async def prompt_operator(task: str, agent: str = "Agent", variety: str = "Honeycrisp") -> dict[str, Any]:
    """Wait for an explicit desktop decision; unavailable review raises an error."""
    return await await_review(task, agent, variety)
