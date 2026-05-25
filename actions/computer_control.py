# -*- coding: utf-8 -*-
"""
computer_control.py — System-Level Computer Controller
Manages system power, display, volume, and device controls.
Uses platform-appropriate commands for each OS.
"""

import os
import platform
import subprocess
import sys
import threading
import time
from typing import Optional

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

_SYSTEM = platform.system()


def _run_cmd(cmd: list[str], timeout: float = 5.0) -> tuple[bool, str]:
    """Run a system command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or "OK"
        return False, result.stderr.strip() or f"Exit code: {result.returncode}"
    except FileNotFoundError:
        return False, f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def computer_control(parameters: dict = None, player=None) -> str:
    """
    Main entry point for computer control.

    Args:
        parameters: Dict with action and params
        player: UI player for logging

    Returns:
        Status string describing the result.
    """
    params = parameters or {}
    action = params.get("action", "status").strip().lower()

    if player:
        player.write_log(f"[ComputerControl] Action: {action}")

    # ── System Info ─────────────────────────────────────────────────
    if action == "status" or action == "info":
        import psutil
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            boot_time = psutil.boot_time()

            return (
                f"System Status:\n"
                f"  OS: {_SYSTEM} {platform.release()}\n"
                f"  CPU: {cpu_percent}% used ({psutil.cpu_count()} cores)\n"
                f"  Memory: {memory.used // (1024**3)}GB / "
                f"{memory.total // (1024**3)}GB ({memory.percent}%)\n"
                f"  Disk: {disk.used // (1024**3)}GB / "
                f"{disk.total // (1024**3)}GB ({disk.percent}%)\n"
                f"  Uptime: {int((time.time() - boot_time) / 3600)}h"
                f"{int((time.time() - boot_time) % 3600 / 60)}m\n"
                f"  Hostname: {platform.node()}"
            )
        except ImportError:
            return (
                f"System Status:\n"
                f"  OS: {_SYSTEM} {platform.release()}\n"
                f"  Hostname: {platform.node()}\n"
                f"  Python: {sys.version.split()[0]}\n"
                f"  Install psutil for detailed stats: pip install psutil"
            )

    # ── Shutdown ───────────────────────────────────────────────────
    elif action == "shutdown":
        confirm = params.get("confirm", "").strip().lower()
        if confirm != "yes":
            return (
                "⚠️ Shutdown requires confirmation. "
                "Set confirm='yes' to proceed."
            )

        if player:
            player.write_log("[ComputerControl] SHUTDOWN initiated by user")

        delay = params.get("delay", 60)
        if _SYSTEM == "Windows":
            subprocess.Popen(["shutdown", "/s", "/t", str(delay)])
            return f"System will shut down in {delay} seconds. Use 'abort_shutdown' to cancel."
        elif _SYSTEM == "Linux" or _SYSTEM == "Darwin":
            subprocess.Popen(["shutdown", "-h", f"+{delay // 60}"])
            return f"System will shut down in {delay} seconds."
        return "Shutdown not supported on this OS."

    # ── Reboot ─────────────────────────────────────────────────────
    elif action == "reboot" or action == "restart":
        confirm = params.get("confirm", "").strip().lower()
        if confirm != "yes":
            return (
                "⚠️ Reboot requires confirmation. "
                "Set confirm='yes' to proceed."
            )

        if player:
            player.write_log("[ComputerControl] REBOOT initiated by user")

        delay = params.get("delay", 60)
        if _SYSTEM == "Windows":
            subprocess.Popen(["shutdown", "/r", "/t", str(delay)])
            return f"System will reboot in {delay} seconds. Use 'abort_shutdown' to cancel."
        elif _SYSTEM == "Linux" or _SYSTEM == "Darwin":
            subprocess.Popen(["shutdown", "-r", f"+{delay // 60}"])
            return f"System will reboot in {delay} seconds."
        return "Reboot not supported on this OS."

    # ── Abort Shutdown ─────────────────────────────────────────────
    elif action == "abort_shutdown" or action == "cancel_shutdown":
        if _SYSTEM == "Windows":
            subprocess.run(["shutdown", "/a"], capture_output=True)
            return "Shutdown/reboot cancelled."
        elif _SYSTEM == "Linux" or _SYSTEM == "Darwin":
            subprocess.run(["shutdown", "-c"], capture_output=True)
            return "Shutdown/reboot cancelled."
        return "Abort not supported on this OS."

    # ── Lock ───────────────────────────────────────────────────────
    elif action == "lock":
        if _SYSTEM == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        elif _SYSTEM == "Darwin":
            subprocess.run(["pmset", "displaysleepnow"])
        else:
            subprocess.run(["gnome-screensaver-command", "--lock"])
        return "System locked."

    # ── Sleep ──────────────────────────────────────────────────────
    elif action == "sleep":
        if _SYSTEM == "Windows":
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
        elif _SYSTEM == "Darwin":
            subprocess.run(["pmset", "sleepnow"])
        else:
            subprocess.run(["systemctl", "suspend"])
        return "System entering sleep mode."

    # ── Volume ─────────────────────────────────────────────────────
    elif action == "volume":
        level = params.get("level")
        if level is not None:
            level = max(0, min(100, int(level)))
            if _SYSTEM == "Windows":
                try:
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    from ctypes import cast, POINTER
                    from comtypes import CLSCTX_ALL
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(
                        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                    )
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                    return f"Volume set to {level}%."
                except ImportError:
                    return (
                        "Volume control requires pycaw on Windows. "
                        "Install: pip install pycaw comtypes"
                    )
            elif _SYSTEM == "Darwin":
                ok, out = _run_cmd([
                    "osascript", "-e",
                    f"set volume output volume {level}"
                ])
                return f"Volume set to {level}%." if ok else f"Volume failed: {out}"
            else:
                ok, out = _run_cmd(["amixer", "set", "Master", f"{level}%"])
                return f"Volume set to {level}%." if ok else f"Volume failed: {out}"
        else:
            return "Specify 'level' parameter (0-100)."

    # ── Mute ───────────────────────────────────────────────────────
    elif action == "mute":
        if _SYSTEM == "Windows":
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                )
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMute(1, None)
                return "System muted."
            except ImportError:
                return "Mute requires pycaw. Install: pip install pycaw comtypes"
        elif _SYSTEM == "Darwin":
            _run_cmd(["osascript", "-e", "set volume output muted true"])
            return "System muted."
        else:
            _run_cmd(["amixer", "set", "Master", "mute"])
            return "System muted."

    # ── Unmute ─────────────────────────────────────────────────────
    elif action == "unmute":
        if _SYSTEM == "Windows":
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                )
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMute(0, None)
                return "System unmuted."
            except ImportError:
                return "Unmute requires pycaw. Install: pip install pycaw comtypes"
        elif _SYSTEM == "Darwin":
            _run_cmd(["osascript", "-e", "set volume output muted false"])
            return "System unmuted."
        else:
            _run_cmd(["amixer", "set", "Master", "unmute"])
            return "System unmuted."

    # ── Display Brightness ─────────────────────────────────────────
    elif action == "brightness":
        level = params.get("level")
        if level is not None:
            level = max(0, min(100, int(level)))
            if _SYSTEM == "Windows":
                try:
                    import screen_brightness_control as sbc
                    sbc.set_brightness(level)
                    return f"Brightness set to {level}%."
                except ImportError:
                    return (
                        "Brightness control requires screen-brightness-control. "
                        "Install: pip install screen-brightness-control"
                    )
            elif _SYSTEM == "Darwin":
                ok, out = _run_cmd([
                    "brightness", str(level / 100.0)
                ])
                return f"Brightness set to {level}%." if ok else (
                    "Brightness control requires 'brightness' CLI tool."
                )
            else:
                # Linux - try xbacklight or ddcutil
                ok, _ = _run_cmd(["xbacklight", "-set", str(level)])
                if ok:
                    return f"Brightness set to {level}%."
                return (
                    "Brightness control requires xbacklight (Linux) "
                    "or screen-brightness-control (cross-platform)."
                )
        else:
            return "Specify 'level' parameter (0-100)."

    # ── Screenshot ─────────────────────────────────────────────────
    elif action == "screenshot":
        if not _PYAUTOGUI:
            return "Screenshot requires pyautogui. Install: pip install pyautogui"

        output_dir = Path(__file__).resolve().parent.parent / "outputs"
        output_dir.mkdir(exist_ok=True)
        timestamp = int(time.time())
        path = output_dir / f"screenshot_{timestamp}.png"

        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(str(path))
            return f"Screenshot saved to: {path}"
        except Exception as e:
            return f"Screenshot failed: {e}"

    # ── Empty Trash ────────────────────────────────────────────────
    elif action == "empty_trash" or action == "clean":
        if _SYSTEM == "Windows":
            subprocess.run(["cmd", "/c", "rd", "/s", "/q", "%temp%"], shell=True)
            return "Temporary files cleaned."
        elif _SYSTEM == "Darwin":
            subprocess.run(["rm", "-rf", "~/.Trash/*"], shell=True)
            return "Trash emptied."
        else:
            subprocess.run(["rm", "-rf", "~/.local/share/Trash/*"], shell=True)
            return "Trash emptied."

    # ── Notify ─────────────────────────────────────────────────────
    elif action == "notify":
        title = params.get("title", "RUMI Notification")
        message = params.get("message", "")
        if not message:
            return "Specify a 'message' parameter."

        try:
            if _SYSTEM == "Windows":
                from plyer import notification
                notification.notify(
                    title=title,
                    message=message,
                    timeout=5,
                )
            elif _SYSTEM == "Darwin":
                subprocess.run([
                    "osascript", "-e",
                    f'display notification "{message}" with title "{title}"'
                ])
            else:
                subprocess.run(["notify-send", title, message])
            return f"Notification sent: {title}"
        except ImportError:
            return f"Notification: {title} — {message} (install plyer for native)"
        except Exception as e:
            return f"Notification failed: {e}"

    else:
        return (
            f"Unknown action: {action}. "
            f"Available: status, shutdown, reboot, lock, sleep, "
            f"volume, mute, unmute, brightness, screenshot, "
            f"notify, abort_shutdown, clean"
        )
