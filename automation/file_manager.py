"""
Nova 3.0 - File manager.

Local filesystem operations, gated behind Config.ENABLE_SYSTEM_CONTROL for
the same reason as automation/system_control.py: these only make sense when
Nova runs locally on the machine whose files you want touched.

All paths are resolved relative to the user's home directory and validated
to prevent path traversal outside of well-known folders.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from config.config import Config

HOME = Path.home()

KNOWN_FOLDERS = {
    "downloads": HOME / "Downloads",
    "pictures": HOME / "Pictures",
    "videos": HOME / "Videos",
    "music": HOME / "Music",
    "desktop": HOME / "Desktop",
    "documents": HOME / "Documents",
}


class FileOperationError(Exception):
    pass


def _guard() -> None:
    if not Config.ENABLE_SYSTEM_CONTROL:
        raise FileOperationError(
            "File operations are disabled. Set ENABLE_SYSTEM_CONTROL=true in "
            ".env only when running Nova locally."
        )


def _safe_path(path_str: str) -> Path:
    """Resolve a user-supplied path and ensure it stays under the home dir."""
    candidate = (HOME / path_str).resolve() if not os.path.isabs(path_str) else Path(path_str).resolve()
    if HOME not in candidate.parents and candidate != HOME:
        raise FileOperationError(f"Refusing to operate outside the home directory: {candidate}")
    return candidate


def create_folder(folder_name: str, parent: str = "desktop") -> str:
    _guard()
    base = KNOWN_FOLDERS.get(parent.lower(), HOME / parent)
    target = base / folder_name
    target.mkdir(parents=True, exist_ok=True)
    return f"Created folder: {target}"


def delete_path(path_str: str) -> str:
    _guard()
    target = _safe_path(path_str)
    if not target.exists():
        raise FileOperationError(f"Path does not exist: {target}")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return f"Deleted: {target}"


def move_path(source: str, destination: str) -> str:
    _guard()
    src = _safe_path(source)
    dst = _safe_path(destination)
    shutil.move(str(src), str(dst))
    return f"Moved {src} -> {dst}"


def copy_path(source: str, destination: str) -> str:
    _guard()
    src = _safe_path(source)
    dst = _safe_path(destination)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    return f"Copied {src} -> {dst}"


def rename_path(source: str, new_name: str) -> str:
    _guard()
    src = _safe_path(source)
    dst = src.parent / new_name
    src.rename(dst)
    return f"Renamed {src} -> {dst}"


def open_known_folder(folder_name: str) -> str:
    _guard()
    target = KNOWN_FOLDERS.get(folder_name.lower())
    if not target:
        raise FileOperationError(f"Unknown folder: {folder_name}")
    target.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        os.startfile(target)  # type: ignore[attr-defined]
    else:
        opener = "open" if os.uname().sysname == "Darwin" else "xdg-open"
        os.system(f'{opener} "{target}"')
    return f"Opened {target}"
