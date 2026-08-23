"""Cross-platform path and location helpers.

Wraps :class:`Gio.File`, :mod:`pathlib` and :func:`GLib.get_user_special_dir`
into a single namespace so the UI does not need to care about the OS it runs on.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from gi.repository import Gio, GLib

IS_LINUX = sys.platform.startswith("linux")
IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"

# Convenience alias.
G_FILE = Gio.File

HOME_DIR = Path.home()


def user_home() -> Path:
    return HOME_DIR


def _special_dir(kind: GLib.UserDirectory) -> Optional[Path]:
    path = GLib.get_user_special_dir(kind)
    if path:
        return Path(path)
    return None


def user_desktop() -> Path:
    return _special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP) or HOME_DIR


def user_documents() -> Path:
    return _special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS) or HOME_DIR / "Documents"


def user_downloads() -> Path:
    return _special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) or HOME_DIR / "Downloads"


def user_music() -> Path:
    return _special_dir(GLib.UserDirectory.DIRECTORY_MUSIC) or HOME_DIR / "Music"


def user_pictures() -> Path:
    return _special_dir(GLib.UserDirectory.DIRECTORY_PICTURES) or HOME_DIR / "Pictures"


def user_videos() -> Path:
    return _special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS) or HOME_DIR / "Videos"


def special_navigation() -> list[tuple[str, Path, str]]:
    """Return (label, path, icon) tuples for the default navigation section.

    Labels are intentionally plain identifiers; the UI translates them.
    """
    return [
        ("home", user_home(), "user-home"),
        ("desktop", user_desktop(), "user-desktop"),
        ("documents", user_documents(), "folder-documents"),
        ("downloads", user_downloads(), "folder-download"),
        ("pictures", user_pictures(), "folder-pictures"),
        ("music", user_music(), "folder-music"),
        ("videos", user_videos(), "folder-videos"),
    ]


def path_to_file(path: str | os.PathLike[str]) -> Gio.File:
    return Gio.File.new_for_path(os.fspath(path))


def file_to_path(p: Gio.File) -> Path:
    return Path(p.get_path())


def is_hidden_path(path: Path) -> bool:
    """Heuristic: a path is hidden when any of its components start with a dot."""
    return any(part.startswith(".") and part not in (".", "..") for part in path.parts)


def display_name(path: Path) -> str:
    return path.name or str(path)


def home_or_root() -> Path:
    return HOME_DIR


def normalize(path: Path) -> Path:
    return path.expanduser().resolve()


def kind_label(info: Gio.FileInfo) -> str:
    """Return a human friendly (untagged) label for a file's type."""
    ftype = info.get_file_type()
    if ftype == Gio.FileType.DIRECTORY:
        return "folder"
    if ftype == Gio.FileType.MOUNTABLE:
        return "drive"
    if ftype == Gio.FileType.SYMBOLIC_LINK:
        return "link"
    if ftype == Gio.FileType.SPECIAL:
        return "special"
    if ftype == Gio.FileType.SHORTCUT:
        return "shortcut"
    return "file"
