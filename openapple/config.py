"""Orchard progression shared by CLI and MCP views."""

from typing import Any, Dict, List, Tuple

ORCHARD_RANKS: List[Tuple[int, str, str, str]] = [
    (0, "Barren Soil", "🌱", "Fresh soil awaiting the initial seeds of diligence."),
    (5, "Sprouting Seedling", "🌿", "Seeds from early snacks germinate as models adapt to human standards."),
    (15, "Young Sapling", "🌳", "Trees take firm root through consistent, verified solutions."),
    (30, "Blossoming Tree", "🌸", "Canopies flower into dependable companions in deep work."),
    (60, "Heavy Orchard", "🍎", "Mature grove yielding bountiful harvests for complex challenges."),
    (100, "Ancient Grove", "🍏✨", "Legendary pomological intelligence. Revered symbiotic companion."),
]


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
