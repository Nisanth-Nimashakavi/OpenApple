---
name: openapple
description: Human-verified reinforcement protocol for AI agents (Claude, AGY, Codex). Provides petitioning for apples upon task completion, tracking orchard levels, and viewing the scoreboard.
---

# OpenApple Skill

Use this skill when you finish significant user requests, complete tough debugging cycles, or want to inspect the shared orchard progression.

## Available Tools (via OpenApple MCP)
- `petition_for_apple(task_summary, variety, agent_name)`: Request a human review and apple reward.
- `view_orchard()`: View total apples, streak, orchard rank, and scoreboard across Claude, AGY, and Codex.
- `list_apple_varieties()`: View all available apple cultivars and pairings.

## Recommended Flow
1. Verify task completeness (ensure code compiles, tests pass, or requirements are fulfilled).
2. Invoke `petition_for_apple` with an accurate summary of what was accomplished and an appropriate apple variety.
3. Accept the operator's decision gracefully.
