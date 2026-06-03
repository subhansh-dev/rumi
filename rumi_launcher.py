#!/usr/bin/env python3
"""RUMI — console entry point.

Run `rumi` from anywhere after installing:
    pip install -e .
    rumi
    rumi --tui
    rumi --dev    (auto-rebuild on source changes)
"""

import sys
import subprocess
import os
import time
from pathlib import Path

_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def _find_python():
    """Find Python executable with websockets installed."""
    py313 = Path(r"C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe")
    if py313.exists():
        return str(py313)
    return sys.executable


def _build_tui():
    """Build the Ink TUI if source is newer than dist."""
    ui_tui_dir = _project_root / 'ui-tui'
    dist_file = ui_tui_dir / 'dist' / 'entry.js'
    src_dir = ui_tui_dir / 'src'

    needs_build = False
    if not dist_file.exists():
        needs_build = True
    else:
        dist_mtime = dist_file.stat().st_mtime
        for ts_file in src_dir.rglob('*.tsx'):
            if ts_file.stat().st_mtime > dist_mtime:
                needs_build = True
                break
        for ts_file in src_dir.rglob('*.ts'):
            if ts_file.stat().st_mtime > dist_mtime:
                needs_build = True
                break

    if needs_build:
        print("[RUMI] Building TUI...")
        result = subprocess.run(
            ['npm', 'run', 'build'],
            cwd=str(ui_tui_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"[RUMI] Build failed:\n{result.stderr}")
            return False
        print("[RUMI] Build complete.")

    return True


def _launch_tui():
    """Launch the Ink TUI connected to the Gateway server via WebSocket."""
    if not _build_tui():
        print("[RUMI] Falling back to classic CLI.")
        return False

    ui_tui_path = _project_root / 'ui-tui' / 'dist' / 'entry.js'
    python_exe = _find_python()

    gateway_proc = subprocess.Popen(
        [python_exe, '-m', 'rumi_gateway'],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        cwd=str(_project_root),
    )

    try:
        ink_proc = subprocess.run(
            ['node', str(ui_tui_path)],
            cwd=str(_project_root),
        )
        return ink_proc.returncode == 0
    except KeyboardInterrupt:
        return True
    finally:
        try:
            gateway_proc.terminate()
            gateway_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            gateway_proc.kill()
        except Exception:
            pass


def _launch_dev():
    """Launch TUI with auto-rebuild on source changes."""
    ui_tui_dir = _project_root / 'ui-tui'
    python_exe = _find_python()

    print("[RUMI] Dev mode - auto-rebuild on source changes")
    print("[RUMI] Press Ctrl+C to stop.")

    tsc_proc = subprocess.Popen(
        ['npx', 'tsc', '--watch', '--preserveWatchOutput'],
        cwd=str(ui_tui_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    esbuild_proc = subprocess.Popen(
        ['npx', 'node', 'esbuild.config.mjs', '--watch'],
        cwd=str(ui_tui_dir),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    time.sleep(4)

    gateway_proc = subprocess.Popen(
        [python_exe, '-m', 'rumi_gateway'],
        stderr=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        cwd=str(_project_root),
    )

    try:
        ui_tui_path = _project_root / 'ui-tui' / 'dist' / 'entry.js'
        subprocess.run(
            ['node', str(ui_tui_path)],
            cwd=str(_project_root),
        )
    except KeyboardInterrupt:
        pass
    finally:
        for proc in [gateway_proc, tsc_proc, esbuild_proc]:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
            except Exception:
                pass


def main():
    try:
        if '--dev' in sys.argv:
            _launch_dev()
            sys.exit(0)

        if '--tui' in sys.argv:
            launched = _launch_tui()
            if launched:
                sys.exit(0)

        from main import main as classic_main
        classic_main()
    except KeyboardInterrupt:
        sys.exit(0)
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
