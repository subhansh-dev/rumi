#!/usr/bin/env python3
"""RUMI — console entry point.

Run `rumi` from anywhere after installing:
    pip install -e .
    rumi
    rumi --tui
"""

import sys
import subprocess
from pathlib import Path

_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def _launch_tui():
    """Launch the Ink TUI connected to the Gateway server via pipes."""
    ui_tui_path = _project_root / 'ui-tui' / 'dist' / 'entry.js'
    if not ui_tui_path.exists():
        print("[RUMI] ui-tui not built. Run: cd ui-tui && npm run build")
        print("[RUMI] Falling back to classic CLI.")
        return False

    gateway_proc = subprocess.Popen(
        [sys.executable, '-m', 'rumi_gateway'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        cwd=str(_project_root),
    )
    ink_proc = subprocess.Popen(
        ['node', str(ui_tui_path)],
        stdin=gateway_proc.stdout,
        stdout=gateway_proc.stdin,
    )
    try:
        ink_proc.wait()
    finally:
        gateway_proc.stdin.close()
        gateway_proc.stdout.close()
        gateway_proc.terminate()
        gateway_proc.wait()
    return True


def main():
    if '--tui' in sys.argv:
        launched = _launch_tui()
        if launched:
            sys.exit(0)
        # Fall through to classic CLI if TUI not built

    from main import main as classic_main
    classic_main()


if __name__ == "__main__":
    main()
