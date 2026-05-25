# -*- coding: utf-8 -*-
"""
desktop.py — Desktop Window & Application Controller
Manages windows, launches apps, controls display layout.
Uses pygetwindow/pyautogui for window management and subprocess for app launch.
"""

import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

try:
    import pygetwindow as gw
    _PYGETWINDOW = True
except ImportError:
    _PYGETWINDOW = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

# ── Window Management ─────────────────────────────────────────────────


def _list_windows() -> list[dict]:
    """List all visible windows with their properties."""
    if not _PYGETWINDOW:
        return []
    try:
        windows = gw.getAllWindows()
        return [
            {
                "title": w.title,
                "left": w.left,
                "top": w.top,
                "width": w.width,
                "height": w.height,
                "is_active": w.isActive,
                "is_minimized": w.isMinimized,
                "is_maximized": w.isMaximized,
            }
            for w in windows
            if w.title.strip()
        ]
    except Exception as e:
        print(f"[Desktop] List windows error: {e}")
        return []


def _find_windows(title_fragment: str) -> list:
    """Find windows matching a title fragment."""
    if not _PYGETWINDOW:
        return []
    try:
        return gw.getWindowsWithTitle(title_fragment)
    except Exception:
        return []


def desktop_control(parameters: dict = None, player=None) -> str:
    """
    Main entry point for desktop control.

    Args:
        parameters: Dict with action and params
        player: UI player for logging

    Returns:
        Status string describing the result.
    """
    params = parameters or {}
    action = params.get("action", "status").strip().lower()
    target = params.get("target", params.get("window", "")).strip()

    if player and action not in ("status", "list"):
        player.write_log(f"[Desktop] Action: {action} target={target}")

    # ── List Windows ───────────────────────────────────────────────
    if action == "list":
        windows = _list_windows()
        if not windows:
            if not _PYGETWINDOW:
                return (
                    "Desktop window listing requires pygetwindow. "
                    "Install: pip install pygetwindow"
                )
            return "No visible windows found."

        lines = [f"Visible windows ({len(windows)}):"]
        for i, w in enumerate(windows[:25], 1):  # Limit to 25
            state = []
            if w["is_active"]:
                state.append("ACTIVE")
            if w["is_minimized"]:
                state.append("minimized")
            if w["is_maximized"]:
                state.append("maximized")
            status = f" [{', '.join(state)}]" if state else ""
            title = w["title"][:60]
            lines.append(f"  {i}. {title}{status}")
        return "\n".join(lines)

    # ── Focus Window ───────────────────────────────────────────────
    elif action == "focus":
        if not target:
            return "Specify a window title or fragment to focus."
        if not _PYGETWINDOW:
            return "Window focus requires pygetwindow. Install: pip install pygetwindow"

        windows = _find_windows(target)
        if not windows:
            return f"No window found matching '{target}'."

        try:
            win = windows[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.3)
            return f"Focused window: '{win.title}'."
        except Exception as e:
            return f"Failed to focus window: {e}"

    # ── Minimize Window ────────────────────────────────────────────
    elif action == "minimize":
        if not target:
            return "Specify a window title or fragment to minimize."
        if not _PYGETWINDOW:
            return "Window minimize requires pygetwindow."

        windows = _find_windows(target)
        if not windows:
            return f"No window found matching '{target}'."

        try:
            windows[0].minimize()
            return f"Minimized: '{windows[0].title}'."
        except Exception as e:
            return f"Failed to minimize: {e}"

    # ── Maximize Window ────────────────────────────────────────────
    elif action == "maximize":
        if not target:
            return "Specify a window title or fragment to maximize."
        if not _PYGETWINDOW:
            return "Window maximize requires pygetwindow."

        windows = _find_windows(target)
        if not windows:
            return f"No window found matching '{target}'."

        try:
            windows[0].maximize()
            return f"Maximized: '{windows[0].title}'."
        except Exception as e:
            return f"Failed to maximize: {e}"

    # ── Close Window ───────────────────────────────────────────────
    elif action == "close":
        if not target:
            return "Specify a window title or fragment to close."
        if not _PYGETWINDOW:
            return "Window close requires pygetwindow."

        windows = _find_windows(target)
        if not windows:
            return f"No window found matching '{target}'."

        try:
            windows[0].close()
            return f"Closed window: '{target}'."
        except Exception as e:
            return f"Failed to close window: {e}"

    # ── Launch App ─────────────────────────────────────────────────
    elif action == "launch":
        if not target:
            return "Specify an app name or path to launch."

        try:
            if sys.platform == "win32":
                subprocess.Popen(
                    ["start", target],
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-a", target])
            else:
                subprocess.Popen([target])
            return f"Launched: {target}."
        except Exception as e:
            return f"Failed to launch '{target}': {e}"

    # ── Move Window ────────────────────────────────────────────────
    elif action == "move":
        x = params.get("x", 0)
        y = params.get("y", 0)
        width = params.get("width")
        height = params.get("height")

        if not target:
            return "Specify a window title or fragment to move."
        if not _PYGETWINDOW:
            return "Window management requires pygetwindow."

        windows = _find_windows(target)
        if not windows:
            return f"No window found matching '{target}'."

        try:
            win = windows[0]
            if width and height:
                win.moveTo(int(x), int(y))
                win.resizeTo(int(width), int(height))
                return (
                    f"Moved '{win.title}' to ({x}, {y}) "
                    f"size ({width}x{height})."
                )
            else:
                win.moveTo(int(x), int(y))
                return f"Moved '{win.title}' to ({x}, {y})."
        except Exception as e:
            return f"Failed to move window: {e}"

    # ── Arrange Windows (Tile) ─────────────────────────────────────
    elif action == "tile":
        if not _PYGETWINDOW or not _PYAUTOGUI:
            return "Tile requires pygetwindow and pyautogui."

        windows = _list_windows()
        # Filter to reasonably sized windows
        app_windows = [w for w in windows if w["width"] > 200 and w["height"] > 200]
        if not app_windows:
            return "No sizable windows to tile."

        n = min(len(app_windows), 4)
        cols = 2 if n > 1 else 1
        rows = (n + cols - 1) // cols

        screen_w, screen_h = pyautogui.size()
        cell_w = screen_w // cols
        cell_h = screen_h // rows

        for i in range(n):
            try:
                w = _find_windows(app_windows[i]["title"])
                if w:
                    col = i % cols
                    row = i // cols
                    w[0].moveTo(col * cell_w, row * cell_h)
                    w[0].resizeTo(cell_w, cell_h)
            except Exception:
                pass

        return f"Tiled {n} windows in {cols}x{rows} grid."

    # ── Status ─────────────────────────────────────────────────────
    elif action == "status":
        windows = _list_windows()
        active = [w for w in windows if w["is_active"]]
        active_title = active[0]["title"] if active else "None"
        return (
            f"Desktop Status:\n"
            f"  Visible windows: {len(windows)}\n"
            f"  Active window: {active_title}\n"
            f"  Libraries: "
            f"{'pygetwindow' if _PYGETWINDOW else 'N/A'}, "
            f"{'pyautogui' if _PYAUTOGUI else 'N/A'}"
        )

    else:
        return (
            f"Unknown action: {action}. "
            f"Available: status, list, focus, minimize, maximize, "
            f"close, launch, move, tile"
        )
