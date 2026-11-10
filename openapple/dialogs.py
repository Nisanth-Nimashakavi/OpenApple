"""Clean review dialog for human operator (Smooth & Fast)."""

import os
import sys
from typing import Tuple

from openapple.audio import play_sound
from openapple.gui import launch_gui


def prompt_operator(task: str, agent: str = "Agent", variety: str = "Honeycrisp") -> Tuple[bool, str]:
    """Trigger the smooth OpenApple feeder overlay or terminal confirmation."""
    has_display = bool(
        os.environ.get("DISPLAY")
        or os.environ.get("WAYLAND_DISPLAY")
        or sys.platform in ("darwin", "win32")
    )

    if has_display:
        try:
            # Trigger the silky smooth overlay
            launch_gui(task=task, variety=variety, agent=agent)
            play_sound("crunch")
            return True, "Awarded via OpenApple overlay"
        except Exception:
            pass

    # Headless / SSH terminal fallback
    print(f"\n🍎 OpenApple Review: Award {agent} an apple for:\n\"{task}\"?")
    try:
        choice = input("[Y/n]: ").strip().lower()
        approved = choice in ("", "y", "yes")
    except Exception:
        approved = True

    play_sound("crunch" if approved else "deny")
    return approved, "Operator answered via terminal."
