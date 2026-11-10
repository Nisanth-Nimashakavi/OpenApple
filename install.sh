#!/usr/bin/env bash
# OpenApple One-Click Installer for Linux & macOS
set -e

echo "🍎 Installing OpenApple..."

# 1. Detect Python
if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
else
    echo "❌ Error: Python 3 is required but not found. Please install Python 3.10+."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 2. Install Node dependencies (Electron desktop overlay)
if command -v npm >/dev/null 2>&1; then
    echo "⚡ Installing Electron overlay dependencies..."
    npm install --no-audit --prefer-offline || npm install
elif command -v pnpm >/dev/null 2>&1; then
    pnpm install
elif command -v yarn >/dev/null 2>&1; then
    yarn install
else
    echo "ℹ️  Node.js / npm not found. Python CLI and MCP server will work, but install Node.js for the smooth cursor overlay."
fi

# 3. Install Python package
if command -v uv >/dev/null 2>&1; then
    echo "⚡ Installing with uv..."
    uv pip install -e . || pip install -e .
else
    echo "📦 Installing with pip..."
    pip install -e .
fi

# 4. Link CLI binaries to ~/.local/bin
mkdir -p "$HOME/.local/bin"
for bin_name in openapple openapple-server openapple-gui; do
    if [ -f "$HOME/.venv/bin/$bin_name" ]; then
        ln -sf "$HOME/.venv/bin/$bin_name" "$HOME/.local/bin/$bin_name"
    fi
done

# 5. Run automated agent configuration & health doctor
if command -v openapple >/dev/null 2>&1; then
    openapple install all
    openapple doctor
else
    "$PY_BIN" -m openapple.cli install all
    "$PY_BIN" -m openapple.cli doctor
fi

echo "✨ OpenApple installation complete! Type 'openapple' to spawn your floating apple."
