"""Cross-platform agent installer and environment diagnostics (Linux, macOS, Windows)."""

import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from openapple.config import AGENT_PROFILES, ORCHARD_RANKS, get_orchard_level
from openapple.engine import OpenAppleEngine


def get_agent_config_paths() -> Dict[str, List[Path]]:
    """Return OS-specific configuration file paths for each supported AI agent."""
    home = Path.home()
    sys_name = platform.system()

    paths: Dict[str, List[Path]] = {
        "claude": [],
        "agy": [],
        "codex": [],
    }

    if sys_name == "Darwin":  # macOS
        paths["claude"].append(home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json")
        paths["claude"].append(home / ".claude" / ".claude.json")
        paths["agy"].append(home / ".gemini" / "config" / "mcp_config.json")
        paths["codex"].append(home / ".codex" / "config.toml")
    elif sys_name == "Windows":
        appdata = Path(os.environ.get("APPDATA", str(home / "AppData" / "Roaming")))
        paths["claude"].append(appdata / "Claude" / "claude_desktop_config.json")
        paths["claude"].append(home / ".claude" / ".claude.json")
        paths["agy"].append(home / ".gemini" / "config" / "mcp_config.json")
        paths["codex"].append(home / ".codex" / "config.toml")
    else:  # Linux / Unix
        paths["claude"].append(home / ".config" / "Claude" / "claude_desktop_config.json")
        paths["claude"].append(home / ".claude" / ".claude.json")
        paths["agy"].append(home / ".gemini" / "config" / "mcp_config.json")
        paths["codex"].append(home / ".codex" / "config.toml")

    return paths


def install_mcp_for_json(config_path: Path) -> bool:
    """Safely register OpenApple server in a JSON MCP config file."""
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}

        if "mcpServers" not in data or not isinstance(data["mcpServers"], dict):
            data["mcpServers"] = {}

        data["mcpServers"]["openapple"] = {
            "command": "openapple-server",
        }

        config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"   ⚠️ Could not write {config_path}: {e}")
        return False


def install_mcp_for_toml(config_path: Path) -> bool:
    """Safely register OpenApple server in a TOML config file (Codex)."""
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        content = ""
        if config_path.exists():
            content = config_path.read_text(encoding="utf-8")

        if "[mcp_servers.openapple]" in content:
            return True  # Already registered

        block = '\n\n# --- OpenApple Human Reinforcement Protocol ---\n[mcp_servers.openapple]\ncommand = "openapple-server"\n'
        config_path.write_text(content + block, encoding="utf-8")
        return True
    except Exception as e:
        print(f"   ⚠️ Could not write {config_path}: {e}")
        return False


def install_agent_rules() -> None:
    """Ensure OpenApple rule files exist for active agent ecosystems."""
    home = Path.home()
    rule_content = """# OpenApple Rule: Human Reinforcement Protocol

1. Never award yourself an apple or assume task success is absolute.
2. Upon completing a substantive milestone, challenge, or bugfix, submit a petition via `petition_for_apple`.
3. If the user withholds an apple, view the critique and improve the solution.
"""

    rule_targets = [
        home / ".gemini" / "config" / "rules" / "openapple.md",
        home / ".claude" / "rules" / "openapple.md",
        home / ".codex" / "rules" / "openapple.md",
    ]

    for rt in rule_targets:
        try:
            if rt.parent.exists():
                rt.write_text(rule_content, encoding="utf-8")
        except Exception:
            pass


def install_agents(target: str = "all") -> None:
    """Configure Claude, AGY, and Codex across platforms."""
    paths = get_agent_config_paths()
    target = target.lower()

    print(f"\n🍎 Configuring OpenApple for AI Agents [{target}]...")
    install_agent_rules()

    configured = 0

    if target in ("all", "claude"):
        for p in paths["claude"]:
            if install_mcp_for_json(p):
                print(f"   ✅ Claude Desktop / Code: {p}")
                configured += 1

    if target in ("all", "agy"):
        for p in paths["agy"]:
            if install_mcp_for_json(p):
                print(f"   ✅ Google Antigravity (AGY): {p}")
                configured += 1

    if target in ("all", "codex"):
        for p in paths["codex"]:
            if install_mcp_for_toml(p):
                print(f"   ✅ OpenAI Codex: {p}")
                configured += 1

    print(f"✨ Successfully configured {configured} agent targets.\n")


def run_doctor() -> None:
    """Comprehensive environment diagnostics across Linux, macOS, and Windows."""
    sys_name = platform.system()
    arch = platform.machine()
    py_ver = sys.version.split()[0]
    node_bin = shutil.which("node")
    npm_bin = shutil.which("npm")
    electron_bin = shutil.which("electron") or shutil.which("electron.cmd")

    print("\n" + "=" * 62)
    print(" 🍎  OpenApple Environment Doctor")
    print("=" * 62)

    # 1. Platform & Architecture
    print(f"\n💻 Operating System : {sys_name} ({arch})")
    print(f"🐍 Python Runtime   : {py_ver} ({sys.executable})")

    # 2. Node & Desktop Overlay
    print(f"\n⚡ Desktop Overlay Dependencies:")
    print(f"   • Node.js        : {'✅ ' + node_bin if node_bin else '❌ Not found (install Node.js)'}")
    print(f"   • npm            : {'✅ ' + npm_bin if npm_bin else '❌ Not found'}")
    print(f"   • Electron       : {'✅ ' + electron_bin if electron_bin else 'ℹ️  Managed via npm/bin/openapple.js'}")

    # 3. Keystroke Macro Injector
    print(f"\n⌨️  Keystroke Macro Injector:")
    if sys_name == "Darwin":
        print(f"   • macOS AppleScript (osascript): ✅ Built-in")
    elif sys_name == "Windows":
        has_koffi = False
        try:
            import koffi  # type: ignore
            has_koffi = True
        except ImportError:
            pass
        print(f"   • PowerShell SendKeys / Base64 : ✅ Built-in")
        print(f"   • Win32 FFI (koffi)             : {'✅ Accelerated' if has_koffi else 'ℹ️  Optional (npm i koffi)'}")
    else:  # Linux
        is_hyprland = bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"))
        is_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
        wtype_bin = shutil.which("wtype")
        xdotool_bin = shutil.which("xdotool")

        if is_hyprland:
            print(f"   • Compositor     : Hyprland (Wayland)")
            print(f"   • wtype          : {'✅ ' + wtype_bin if wtype_bin else '⚠️  Missing (run: sudo pacman -S wtype / sudo apt install wtype)'}")
        elif is_wayland:
            print(f"   • Compositor     : Wayland")
            print(f"   • wtype          : {'✅ ' + wtype_bin if wtype_bin else '⚠️  Recommended for Wayland'}")
        else:
            print(f"   • Display Server : X11")
            print(f"   • xdotool        : {'✅ ' + xdotool_bin if xdotool_bin else '⚠️  Missing (run: sudo apt install xdotool)'}")

    # 4. Audio Engine
    print(f"\n🔊 Sound Effects Engine:")
    if sys_name == "Darwin":
        print(f"   • afplay (macOS Native)        : ✅ Ready")
    elif sys_name == "Windows":
        print(f"   • winsound (Windows Native)    : ✅ Ready")
    else:
        players = ["paplay", "pw-play", "canberra-gtk-play", "aplay"]
        found_player = next((p for p in players if shutil.which(p)), None)
        if found_player:
            print(f"   • Linux Audio Player           : ✅ {found_player}")
        else:
            print(f"   • Linux Audio Player           : ⚠️  No player found (install pulseaudio-utils or pipewire)")

    # 5. Agent Integrations
    print(f"\n🤖 AI Agent Integrations:")
    paths = get_agent_config_paths()
    for agent, agent_paths in paths.items():
        found = any(p.exists() for p in agent_paths)
        status = "✅ Active" if found else "⚪ Not detected"
        print(f"   • {agent.upper():<8} : {status}")

    # 6. Orchard Ledger
    engine = OpenAppleEngine()
    total = engine.state.get("total_apples", 0)
    streak = engine.state.get("current_streak", 0)
    level_info = get_orchard_level(total)

    print(f"\n🌳 Orchard Health:")
    print(f"   • Apples Fed     : {total}")
    print(f"   • Current Streak : {streak} in a row 🌟")
    print(f"   • Grove Rank     : {level_info['name']} {level_info['emoji']}")
    print("=" * 62 + "\n")
