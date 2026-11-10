"""Configuration constants, paths, ranks, and ASCII art for OpenApple."""

from pathlib import Path
from typing import Any, Dict, List, Tuple

# Storage paths
OPENAPPLE_DIR = Path.home() / ".openapple"
LEDGER_PATH = OPENAPPLE_DIR / "ledger.json"
PENDING_PATH = OPENAPPLE_DIR / "pending.json"
SOUNDS_DIR = OPENAPPLE_DIR / "sounds"

# Supported primary agents
SUPPORTED_AGENTS = ["claude", "agy", "codex", "universal"]

# Agent display profiles
AGENT_PROFILES: Dict[str, Dict[str, str]] = {
    "claude": {
        "display_name": "Claude",
        "emoji": "🤖",
        "icon": "🟣",
        "title": "Anthropic Claude",
    },
    "agy": {
        "display_name": "AGY",
        "emoji": "🚀",
        "icon": "🔵",
        "title": "Google Antigravity (AGY)",
    },
    "codex": {
        "display_name": "Codex",
        "emoji": "⚡",
        "icon": "🟢",
        "title": "OpenAI Codex",
    },
    "universal": {
        "display_name": "Agent",
        "emoji": "🌱",
        "icon": "⚪",
        "title": "Universal LLM Agent",
    },
}

# Orchard Progression System
# (Threshold apples, Rank Name, Emoji, Description)
ORCHARD_RANKS: List[Tuple[int, str, str, str]] = [
    (0, "Barren Soil", "🌱", "Fresh soil awaiting the initial seeds of diligence."),
    (5, "Sprouting Seedling", "🌿", "Seeds from early snacks germinate as models adapt to human standards."),
    (15, "Young Sapling", "🌳", "Trees take firm root through consistent, verified solutions."),
    (30, "Blossoming Tree", "🌸", "Canopies flower into dependable companions in deep work."),
    (60, "Heavy Orchard", "🍎", "Mature grove yielding bountiful harvests for complex challenges."),
    (100, "Ancient Grove", "🍏✨", "Legendary pomological intelligence. Revered symbiotic companion."),
]

ASCII_TREES: Dict[str, str] = {
    "Barren Soil": r"""
           .
         . : .
      -----------
    🌱 Barren Soil
""",
    "Sprouting Seedling": r"""
           \ | /
         --- * ---
           / | \
             |
            /|
           / | \
          '  |  `
      ---------------
    🌿 Sprouting Seedling
""",
    "Young Sapling": r"""
           &&&
         &&&&&&&
        &&&&&&&&&
           |||
           |||
       ------------
    🌳 Young Sapling
""",
    "Blossoming Tree": r"""
          🌸 &&& 🌸
        &&&& 🌸 &&&&
       🌸 &&&&&&&& 🌸
           |||||
           |||||
       -------------
    🌸 Blossoming Tree
""",
    "Heavy Orchard": r"""
          🍎 &&&& 🍎
        &&&& 🍎 &&&&
       🍎 &&&&&&&& 🍎
        &&&& 🍎 &&&&
           |||||
           |||||
      ---------------
    🍎 Heavy Orchard
""",
    "Ancient Grove": r"""
        ✨ 🍏 &&&& 🍏 ✨
       &&&& 🍏 &&&& 🍏
      🍏 &&&& ✨ &&&& 🍏
     ✨ &&&&& 🍏 &&&&& ✨
         |||||||||
         |||||||||
     ~~~~~~~~~~~~~~~~~
    🍏✨ Ancient Grove ✨🍏
""",
}


def get_orchard_level(total_apples: int) -> Dict[str, Any]:
    """Calculate the orchard level based on total apples fed."""
    current_rank = ORCHARD_RANKS[0]
    next_rank = None
    for r in ORCHARD_RANKS:
        if total_apples >= r[0]:
            current_rank = r
        else:
            next_rank = r
            break
    return {
        "name": current_rank[1],
        "emoji": current_rank[2],
        "description": current_rank[3],
        "threshold": current_rank[0],
        "next_threshold": next_rank[0] if next_rank else None,
        "next_name": next_rank[1] if next_rank else None,
    }

