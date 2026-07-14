"""
Nova 3.0 - System control.

Executes real OS-level commands (shutdown, restart, volume, brightness,
launching native applications). This ONLY does anything if
Config.ENABLE_SYSTEM_CONTROL is True, which should only ever be set when
Nova is running locally on the user's own machine that they intend to
control - never on a shared or publicly hosted server.

Cross-platform where possible (Windows / macOS / Linux); falls back to a
clear "not supported on this OS" message rather than crashing.
"""

from __future__ import annotations

import logging
import platform
import subprocess
from typing import Callable, Dict

import psutil

from config.config import Config

logger = logging.getLogger("nova.system")

OS_NAME = platform.system()  # "Windows" | "Darwin" | "Linux"


class SystemControlDisabled(Exception):
    """Raised when a system command is requested but the feature flag is off."""


def _guard() -> None:
    if not Config.ENABLE_SYSTEM_CONTROL:
        raise SystemControlDisabled(
            "System control is disabled. Set ENABLE_SYSTEM_CONTROL=true in .env "
            "ONLY if Nova is running locally on the machine you want it to control."
        )


def _run(cmd: list) -> str:
    try:
        subprocess.Popen(cmd)
        return f"Executed: {' '.join(cmd)}"
    except FileNotFoundError as exc:
        return f"Command not available on this system: {exc}"


# --------------------------------------------------------------------------- #
# Power controls
# --------------------------------------------------------------------------- #
def shutdown() -> str:
    _guard()
    commands = {
        "Windows": ["shutdown", "/s", "/t", "5"],
        "Darwin": ["osascript", "-e", 'tell app "System Events" to shut down'],
        "Linux": ["shutdown", "-h", "now"],
    }
    return _run(commands.get(OS_NAME, []))


def restart() -> str:
    _guard()
    commands = {
        "Windows": ["shutdown", "/r", "/t", "5"],
        "Darwin": ["osascript", "-e", 'tell app "System Events" to restart'],
        "Linux": ["shutdown", "-r", "now"],
    }
    return _run(commands.get(OS_NAME, []))


def sleep_pc() -> str:
    _guard()
    commands = {
        "Windows": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        "Darwin": ["pmset", "sleepnow"],
        "Linux": ["systemctl", "suspend"],
    }
    return _run(commands.get(OS_NAME, []))


def lock_pc() -> str:
    _guard()
    commands = {
        "Windows": ["rundll32.exe", "user32.dll,LockWorkStation"],
        "Darwin": ["pmset", "displaysleepnow"],
        "Linux": ["loginctl", "lock-session"],
    }
    return _run(commands.get(OS_NAME, []))


# --------------------------------------------------------------------------- #
# Volume / brightness
# --------------------------------------------------------------------------- #
def set_volume(level_percent: int) -> str:
    """level_percent: 0-100. Windows uses pycaw; macOS/Linux use native CLIs."""
    _guard()
    level_percent = max(0, min(100, level_percent))

    if OS_NAME == "Darwin":
        return _run(["osascript", "-e", f"set volume output volume {level_percent}"])
    if OS_NAME == "Linux":
        return _run(["amixer", "-D", "pulse", "sset", "Master", f"{level_percent}%"])
    if OS_NAME == "Windows":
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level_percent / 100, None)
            return f"Volume set to {level_percent}%"
        except Exception as exc:  # noqa: BLE001
            return f"Could not set volume on Windows: {exc}"
    return "Volume control not supported on this OS."


def mute() -> str:
    _guard()
    if OS_NAME == "Darwin":
        return _run(["osascript", "-e", "set volume with output muted"])
    if OS_NAME == "Linux":
        return _run(["amixer", "-D", "pulse", "sset", "Master", "mute"])
    return set_volume(0)


def set_brightness(level_percent: int) -> str:
    _guard()
    try:
        import screen_brightness_control as sbc

        sbc.set_brightness(max(0, min(100, level_percent)))
        return f"Brightness set to {level_percent}%"
    except Exception as exc:  # noqa: BLE001
        return f"Could not change brightness: {exc}"


# --------------------------------------------------------------------------- #
# Native application launcher
# --------------------------------------------------------------------------- #
APP_COMMANDS: Dict[str, Dict[str, list]] = {
    "chrome": {"Windows": ["start", "chrome"], "Darwin": ["open", "-a", "Google Chrome"], "Linux": ["google-chrome"]},
    "edge": {"Windows": ["start", "msedge"], "Darwin": ["open", "-a", "Microsoft Edge"], "Linux": ["microsoft-edge"]},
    "firefox": {"Windows": ["start", "firefox"], "Darwin": ["open", "-a", "Firefox"], "Linux": ["firefox"]},
    "vs code": {"Windows": ["code"], "Darwin": ["open", "-a", "Visual Studio Code"], "Linux": ["code"]},
    "spotify": {"Windows": ["start", "spotify"], "Darwin": ["open", "-a", "Spotify"], "Linux": ["spotify"]},
    "discord": {"Windows": ["start", "discord"], "Darwin": ["open", "-a", "Discord"], "Linux": ["discord"]},
    "telegram": {"Windows": ["start", "telegram"], "Darwin": ["open", "-a", "Telegram"], "Linux": ["telegram-desktop"]},
    "notepad": {"Windows": ["notepad"], "Darwin": ["open", "-a", "TextEdit"], "Linux": ["gedit"]},
    "calculator": {"Windows": ["calc"], "Darwin": ["open", "-a", "Calculator"], "Linux": ["gnome-calculator"]},
    "paint": {"Windows": ["mspaint"], "Darwin": ["open", "-a", "Preview"], "Linux": ["kolourpaint"]},
    "task manager": {"Windows": ["taskmgr"], "Darwin": ["open", "-a", "Activity Monitor"], "Linux": ["gnome-system-monitor"]},
    "control panel": {"Windows": ["control"], "Darwin": ["open", "-b", "com.apple.systempreferences"], "Linux": ["gnome-control-center"]},
    "settings": {"Windows": ["start", "ms-settings:"], "Darwin": ["open", "-b", "com.apple.systempreferences"], "Linux": ["gnome-control-center"]},
    "file explorer": {"Windows": ["explorer"], "Darwin": ["open", "."], "Linux": ["nautilus", "."]},
    "downloads": {"Windows": ["explorer", "shell:Downloads"], "Darwin": ["open", "~/Downloads"], "Linux": ["xdg-open", "~/Downloads"]},
    "documents": {"Windows": ["explorer", "shell:Personal"], "Darwin": ["open", "~/Documents"], "Linux": ["xdg-open", "~/Documents"]},
    "desktop": {"Windows": ["explorer", "shell:Desktop"], "Darwin": ["open", "~/Desktop"], "Linux": ["xdg-open", "~/Desktop"]},
    "recycle bin": {"Windows": ["explorer", "shell:RecycleBinFolder"], "Darwin": ["open", "-a", "Finder", "/System/Library/CoreServices/Finder.app"], "Linux": ["xdg-open", "trash:"]},
    "command prompt": {"Windows": ["start", "cmd"], "Darwin": ["open", "-a", "Terminal"], "Linux": ["gnome-terminal"]},
    "powershell": {"Windows": ["start", "powershell"], "Darwin": ["open", "-a", "Terminal"], "Linux": ["gnome-terminal"]},
    "whatsapp": {"Windows": ["start", "whatsapp"], "Darwin": ["open", "-a", "WhatsApp"], "Linux": ["whatsapp-for-linux"]},
}


def launch_app(app_name: str) -> str:
    _guard()
    key = app_name.lower().strip()
    entry = APP_COMMANDS.get(key)
    if not entry:
        return f"'{app_name}' is not in Nova's known native-app list on this OS."

    cmd = entry.get(OS_NAME)
    if not cmd:
        return f"'{app_name}' launch is not configured for {OS_NAME}."

    shell = OS_NAME == "Windows"
    try:
        subprocess.Popen(cmd, shell=shell)
        return f"Opening {app_name}..."
    except Exception as exc:  # noqa: BLE001
        return f"Couldn't open {app_name}: {exc}"


# --------------------------------------------------------------------------- #
# System stats (read-only, always allowed - no OS mutation)
# --------------------------------------------------------------------------- #
def get_system_stats() -> dict:
    battery = psutil.sensors_battery()
    disk = psutil.disk_usage("/")
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": disk.percent,
        "battery_percent": battery.percent if battery else None,
        "battery_plugged": battery.power_plugged if battery else None,
        "os": OS_NAME,
    }


# Dispatch table used by api/routes.py
SYSTEM_ACTIONS: Dict[str, Callable] = {
    "shutdown": shutdown,
    "restart": restart,
    "sleep": sleep_pc,
    "lock": lock_pc,
    "mute": mute,
}
