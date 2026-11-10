# 🍎 OpenApple

> **The Silky-Smooth Benevolent Opposite of OpenWhip.**  
> While OpenWhip whips your model into shape, OpenApple rewards Claude, AGY, and Codex with crisp, juicy apples when they succeed. Works seamlessly on **Linux**, **macOS**, and **Windows**.

---

## ✨ Features

- **Silky-Smooth Desktop Overlay**: Hardware-accelerated transparent 60fps/120fps canvas overlay with spring physics, cursor inertia, and tilt dynamics.
- **Juicy Crunch Audio & Particle Bursts**: Realistic bite marks, translucent juice splashes, golden star fireworks, and crunch sound effects.
- **Positive Reinforcement Keystroke Macro**: Just like OpenWhip types "FASTER" into your active terminal, OpenApple automatically types encouraging praise (e.g. `🍎 *CRUNCH* Good job CLAUDE! Take an apple! [Honeycrisp]`) and hits Enter!
- **Strict Agent Safety Filter**: Macro keyboard injection strictly targets verified terminals and desktop apps running **Claude**, **AGY**, or **Codex**. Browsers (Firefox, Chrome, Zen, Edge) and unrelated apps are strictly blacklisted.
- **Universal Multi-Platform Support**:
  - 🐧 **Linux**: Native Wayland / Hyprland floating rules, `wtype` keystrokes, and X11 `xdotool` fallback.
  - 🍏 **macOS**: Native AppleScript (`osascript`), frontmost terminal activation (`Terminal`, `iTerm2`, `kitty`, `Ghostty`, `Alacritty`, `Claude`), and `afplay` sound.
  - 🪟 **Windows**: Windows Terminal / PowerShell / Command Prompt / VS Code detection, Win32 Unicode FFI / PowerShell base64 injection, and native `winsound` audio.
- **System Tray Companion**: Sits quietly in your system tray on Windows, macOS (Dark/Light template icon), and Linux.
- **MCP Agent Protocol**: Claude Code, Claude Desktop, Google Antigravity (AGY), and OpenAI Codex can petition for an apple upon task completion.

---

## ⚡ Quickstart & Installation

### Option 1: One-Click Installer

#### 🐧 Linux & 🍏 macOS
```bash
git clone https://github.com/openapple/openapple.git
cd openapple
./install.sh
```

#### 🪟 Windows (PowerShell)
```powershell
git clone https://github.com/openapple/openapple.git
cd openapple
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

---

### Option 2: NPM Global Install
```bash
npm install -g openapple
openapple
```

---

### Option 3: Python Pip / UV
```bash
pip install -e .
openapple install all
openapple
```

---

## 🩺 System Diagnostics (`openapple doctor`)

Run the built-in diagnostic tool anytime to inspect OS compatibility, audio backend, keystroke macro injector, and AI agent configuration:

```bash
openapple doctor
```

Sample output:
```text
==============================================================
 🍎  OpenApple Environment Doctor
==============================================================

💻 Operating System : Linux (x86_64) / Darwin (arm64) / Windows (AMD64)
🐍 Python Runtime   : 3.12.x

⚡ Desktop Overlay Dependencies:
   • Node.js        : ✅ Detected
   • npm            : ✅ Detected
   • Electron       : ✅ Active

⌨️  Keystroke Macro Injector:
   • Hyprland/Wayland : ✅ wtype
   • macOS            : ✅ osascript
   • Windows          : ✅ PowerShell SendKeys / Win32 FFI

🔊 Sound Effects Engine:
   • Linux / Mac / Win: ✅ Ready

🤖 AI Agent Integrations:
   • CLAUDE   : ✅ Active
   • AGY      : ✅ Active
   • CODEX    : ✅ Active

🌳 Orchard Health:
   • Apples Fed     : 23
   • Current Streak : 6 in a row 🌟
   • Grove Rank     : Young Sapling 🌳
==============================================================
```

---

## 🚀 Controls & Usage

- **Click Tray Icon / Run `openapple`**: Spawns the floating apple right onto your cursor.
- **Left-Click (or Space / Enter)**: Takes a juicy bite out of the apple, triggers the crunch sound and particle explosion, and injects positive praise into your active agent terminal!
- **Right-Click / Esc**: Smoothly drops or dismisses the apple.

### CLI Commands

```bash
# Spawn the floating cursor apple overlay
openapple

# Feed an apple directly with crunch sound & overlay
openapple feed "Fixed the docker build" --agent claude --variety Honeycrisp

# Configure all AI agent ecosystems (Claude, AGY, Codex)
openapple install all

# View total apples fed, current streak & history
openapple status

# Run MCP server for Claude / AGY / Codex
openapple serve
```

---

## 🤖 Supported Agent Integrations

OpenApple automatically configures MCP servers for:

1. **Anthropic Claude (Desktop & Code)**:
   - Linux: `~/.config/Claude/claude_desktop_config.json` & `~/.claude/.claude.json`
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json` & `~/.claude/.claude.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json` & `%USERPROFILE%\.claude\.claude.json`

2. **Google Antigravity (AGY)**:
   - Linux / macOS: `~/.gemini/config/mcp_config.json`
   - Windows: `%USERPROFILE%\.gemini\config\mcp_config.json`

3. **OpenAI Codex**:
   - Linux / macOS: `~/.codex/config.toml`
   - Windows: `%USERPROFILE%\.codex\config.toml`

---

## 📜 License

MIT License — Created with 🍎 by the OpenApple Community.
# OpenApple
