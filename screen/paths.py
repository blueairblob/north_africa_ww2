"""Read-only game files stay with the build; reviewer files live in writable storage."""
import os
from pathlib import Path
import subprocess
import sys
from functools import lru_cache

ROOT = Path(__file__).resolve().parent.parent


def user_root():
    override = os.environ.get("BENGHAZI_USER_DATA")
    if override:
        return Path(override).expanduser()
    if getattr(sys, "frozen", False):
        local = os.environ.get("LOCALAPPDATA")
        return (Path(local) if local else Path.home() / "AppData" / "Local") / "Benghazi Handicap"
    return ROOT


def user_folder(name):
    return user_root() / name


@lru_cache(maxsize=32)
def _wsl_windows_path(path):
    try:
        return subprocess.check_output(["wslpath", "-w", path], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return path


def display_user_root():
    """The path in the form the player's desktop file manager understands."""
    root = str(user_root())
    return _wsl_windows_path(root) if os.name != "nt" and os.environ.get("WSL_DISTRO_NAME") else root


def open_game_files():
    """Show the player's files in the host file manager, creating an obvious home first."""
    root = user_root()
    for name in ("saves", "screenshots"):
        (root / name).mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(str(root))
    elif os.environ.get("WSL_DISTRO_NAME"):
        subprocess.Popen(["explorer.exe", _wsl_windows_path(str(root))],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(root)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    return root
