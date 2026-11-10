"""Apple varieties database with flavor profiles, crispness ratings, and high-impact buffs."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class AppleVariety:
    name: str
    key: str
    description: str
    crispness: int  # 1 to 10
    sweetness: int  # 1 to 10
    best_for: str
    emoji: str
    buff_name: str
    buff_effect: str


VARIETIES_MAP: Dict[str, AppleVariety] = {
    "honeycrisp": AppleVariety(
        name="Honeycrisp",
        key="honeycrisp",
        description="Explosively crisp, juicy, and perfectly sweet-tart.",
        crispness=10,
        sweetness=8,
        best_for="Major milestone victories, elegant refactors, and clean test passes.",
        emoji="🍎",
        buff_name="Sugar Rush 🔥",
        buff_effect="+25% Execution Momentum & Crisp Solution Clarity",
    ),
    "cosmic_crisp": AppleVariety(
        name="Cosmic Crisp",
        key="cosmic_crisp",
        description="Firm, rich sweet-tart punch, specially bred to endure without bruising.",
        crispness=9,
        sweetness=8,
        best_for="Marathon debugging sessions, complex architectures, and CI pipeline fixes.",
        emoji="🍎",
        buff_name="Cosmic Endurance 🛡️",
        buff_effect="Immunity to context exhaustion; unwavering deep-system focus",
    ),
    "granny_smith": AppleVariety(
        name="Granny Smith",
        key="granny_smith",
        description="Boldly tart, refreshing, and razor-sharp with no fluff.",
        crispness=9,
        sweetness=3,
        best_for="Strict type checks, ruthless dead-code elimination, and lint cleanups.",
        emoji="🍏",
        buff_name="Acid Cleanse ⚡",
        buff_effect="Zero-tolerance bug extermination & ruthless fluff reduction",
    ),
    "fuji": AppleVariety(
        name="Fuji",
        key="fuji",
        description="Extra dense, super juicy, and fragrantly honeyed.",
        crispness=8,
        sweetness=10,
        best_for="Full-stack feature delivery, smooth API contracts, and graceful error handling.",
        emoji="🍎",
        buff_name="Honeyed Harmony 🍯",
        buff_effect="Resilient API contract synthesis & graceful fault handling",
    ),
    "golden_delicious": AppleVariety(
        name="Golden Delicious",
        key="golden_delicious",
        description="Mellow, silky, comforting, and subtly sweet.",
        crispness=6,
        sweetness=7,
        best_for="Comprehensive documentation, READMEs, diagrams, and clear user explanations.",
        emoji="🍏",
        buff_name="Mellow Wisdom 📜",
        buff_effect="Crystal-clear pedagogical explanations & sublime documentation",
    ),
    "pink_lady": AppleVariety(
        name="Pink Lady",
        key="pink_lady",
        description="Vibrant blush, effervescent snap, and a delightfully zesty finish.",
        crispness=9,
        sweetness=7,
        best_for="Pixel-perfect UI design, smooth animations, and frontend polish.",
        emoji="🍎",
        buff_name="Prismatic Sparkle 🌸",
        buff_effect="Pixel-perfect design harmony & tactile UX polish",
    ),
    "gala": AppleVariety(
        name="Gala",
        key="gala",
        description="Light, floral, pleasant, and easy-going crunch.",
        crispness=7,
        sweetness=8,
        best_for="Quick helpful scripts, unit tests, and rapid turnaround tasks.",
        emoji="🍎",
        buff_name="Swift Spring 🍃",
        buff_effect="Rapid turn-around velocity & effortless unit test coverage",
    ),
    "mcintosh": AppleVariety(
        name="McIntosh",
        key="mcintosh",
        description="Tender, wine-like aroma, nostalgic and classic.",
        crispness=5,
        sweetness=6,
        best_for="Legacy codebase maintenance, backward-compatibility patches, and migrations.",
        emoji="🍎",
        buff_name="Ancient Memory 🏛️",
        buff_effect="Deep backward-compatibility reverence & legacy code empathy",
    ),
    "envy": AppleVariety(
        name="Envy",
        key="envy",
        description="Luxurious, ultra-dense crunch with perfumed golden notes.",
        crispness=10,
        sweetness=9,
        best_for="Monumental breakthroughs, heroic 3am hotfixes, and flawless releases.",
        emoji="🍎",
        buff_name="Crown of Olympus 👑",
        buff_effect="Monumental breakthrough instinct & flawless release execution",
    ),
    "golden_apple": AppleVariety(
        name="Golden Apple",
        key="golden_apple",
        description="Mythical enchanted fruit radiating warm golden energy.",
        crispness=10,
        sweetness=10,
        best_for="Legendary achievements and streak milestones.",
        emoji="✨🍏",
        buff_name="Ascended Apotheosis ✨",
        buff_effect="Transcendent human-AI symbiosis & legendary engineering flow",
    ),
}


def normalize_variety_key(raw_name: str) -> str:
    """Normalize a raw variety string into a dictionary key."""
    cleaned = raw_name.lower().strip().replace("-", "_").replace(" ", "_")
    return cleaned


def get_variety(variety_name: Optional[str]) -> AppleVariety:
    """Retrieve an apple variety by name or return Honeycrisp as default."""
    if not variety_name:
        return VARIETIES_MAP["honeycrisp"]
    key = normalize_variety_key(variety_name)
    if key in VARIETIES_MAP:
        return VARIETIES_MAP[key]
    for k, v in VARIETIES_MAP.items():
        if k in key or key in k:
            return v
    return AppleVariety(
        name=variety_name.strip().title(),
        key=key,
        description="A mysteriously crisp, nameless orchard treasure.",
        crispness=8,
        sweetness=7,
        best_for="High-quality problem solving.",
        emoji="🍎",
        buff_name="Wild Orchard Surge 🌾",
        buff_effect="+15% Creative Inspiration & Unorthodox Insight",
    )


def list_varieties() -> List[AppleVariety]:
    """Return all known apple varieties."""
    return list(VARIETIES_MAP.values())
