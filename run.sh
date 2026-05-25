#!/usr/bin/env bash
# ==============================================================================
# RUMI Scientist AI — Unix Launcher (Linux/macOS)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ╔══════════════════════════════════════════════════════╗"
echo "  ║           RUMI Scientist AI  v1.0.0                 ║"
echo "  ║     Autonomous Cognitive AI for Research            ║"
echo "  ╚══════════════════════════════════════════════════════╝"
echo ""

# --- Check Python ---
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 is not installed."
    echo "        Install Python 3.12+ from https://python.org"
    exit 1
fi

# --- Check venv ---
python3 -c "import sys; sys.exit(0 if hasattr(sys, 'real_prefix') or (sys.prefix != sys.base_prefix) else 1)" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[INFO] No virtual environment detected."
    echo "       Consider: python3 -m venv .venv && source .venv/bin/activate"
    echo ""
fi

# --- Dependency check ---
echo "[CHECK] Verifying dependencies..."
python3 -c "import rich; import prompt_toolkit; import numpy; import requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[WARN] Some dependencies are missing. Installing..."
    pip3 install -r requirements.txt
    echo "[OK] Dependencies installed."
else
    echo "[OK] Core dependencies found."
fi
echo ""

# --- Launch RUMI ---
echo "[LAUNCH] Starting RUMI Scientist AI..."
echo ""
python3 rumi_launcher.py
EXIT_CODE=$?

# --- On exit ---
if [ $EXIT_CODE -ne 0 ]; then
    echo "[RUMI] Exited with code $EXIT_CODE"
fi
echo ""
echo "[RUMI] Session ended."
