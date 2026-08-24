"""File system operations built on top of Gio.File.

Every public function here may block (network mounts, big copies) and therefore
should be invoked through :mod:`ribbonfm.core.tasks` from the UI layer. The
functions operate on :class:`Gio.File` instances and return plain Python data so
they are easy to unit test without a running GTK main loop.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from typing import Iterable, Optional

from gi.repository import Gio, GLib

from . import pathutils

# Gio virtual location for the user's Trash (like the Windows Recycle Bin).
TRASH_URI = "trash:///"


def is_trash(location: str) -> bool:
    """True if ``location`` is the virtual Trash URI."""
    return location.startswith("trash://")


# FileInfo attributes we pre-request when enumerating.
_ATTRS = (
    Gio.FILE_ATTRIBUTE_STANDARD_NAME + "," +
    Gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME + "," +
    Gio.FILE_ATTRIBUTE_STANDARD_TYPE + "," +
    Gio.FILE_ATTRIBUTE_STANDARD_SIZE + "," +
    Gio.FILE_ATTRIBUTE_STANDARD_IS_HIDDEN + "," +
    Gio.FILE_ATTRIBUTE_STANDARD_IS_BACKUP + "," +
    Gio.FILE_ATTRIBUTE_STANDARD_SYMLINK_TARGET + "," +
    Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE + "," +
    Gio.FILE_ATTRIBUTE_TIME_MODIFIED + "," +
    Gio.FILE_ATTRIBUTE_TIME_ACCESS + "," +
    Gio.FILE_ATTRIBUTE_UNIX_MODE + "," +
    Gio.FILE_ATTRIBUTE_UNIX_UID + "," +
    Gio.FILE_ATTRIBUTE_UNIX_GID + "," +
    Gio.FILE_ATTRIBUTE_OWNER_USER + "," +
    Gio.FILE_ATTRIBUTE_OWNER_GROUP + "," +
    "trashed::deleted"
    ""
)


@dataclass(frozen=True)
class FileEntry:
    """A single entry of a directory listing."""

    name: str
    display_name: str
    path: str
    uri: str
    is_dir: bool
    is_symlink: bool
    is_hidden: bool
    size: int
    mtime: int  # epoch seconds
    mode: int  # unix mode bits (0 on non-unix)
    uid: int
    gid: int
    owner: str
    group: str
    content_type: str
    symlink_target: str
    trashed: bool
    orig_path: str = ""  # original path before being trashed ("" if not trashed)

    @property
    def is_file(self) -> bool:
        return not self.is_dir and not self.is_symlink


def mode_to_rwx(mode: int) -> str:
    """Convert unix mode bits to an ``rwxr-xr-x`` style string."""
    if mode == 0:
        return ""
    bits = [
        mode & stat.S_IRUSR, mode & stat.S_IWUSR, mode & stat.S_IXUSR,
        mode & stat.S_IRGRP, mode & stat.S_IWGRP, mode & stat.S_IXGRP,
        mode & stat.S_IROTH, mode & stat.S_IWOTH, mode & stat.S_IXOTH,
    ]
    letters = "rwxrwxrwx"
    return "".join(letters[i] if b else "-" for i, b in enumerate(bits))


def _str_of(info: Gio.FileInfo, attr: str) -> str:
    """Read a string attribute only when it exists and is typed as string."""
    if info.has_attribute(attr):
        return info.get_attribute_string(attr) or ""
    return ""


def _uint_of(info: Gio.FileInfo, attr: str) -> int:
    if info.has_attribute(attr):
        return info.get_attribute_uint32(attr)
    return 0


def _entry_from_info(parent_path: str, info: Gio.FileInfo) -> FileEntry:
    name = info.get_name()
    ftype = info.get_file_type()
    mode = _uint_of(info, Gio.FILE_ATTRIBUTE_UNIX_MODE)
    return FileEntry(
        name=name,
        display_name=info.get_display_name(),
        path=os.path.join(parent_path, name),
        uri=_str_of(info, Gio.FILE_ATTRIBUTE_STANDARD_SYMLINK_TARGET),
        is_dir=ftype == Gio.FileType.DIRECTORY,
        is_symlink=ftype == Gio.FileType.SYMBOLIC_LINK or
                   info.get_attribute_boolean(Gio.FILE_ATTRIBUTE_STANDARD_IS_SYMLINK),
        is_hidden=info.get_attribute_boolean(Gio.FILE_ATTRIBUTE_STANDARD_IS_HIDDEN),
        size=info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_STANDARD_SIZE),
        mtime=int(info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_TIME_MODIFIED)) or 0,
        mode=mode,
        uid=_uint_of(info, Gio.FILE_ATTRIBUTE_UNIX_UID),
        gid=_uint_of(info, Gio.FILE_ATTRIBUTE_UNIX_GID),
        owner=_str_of(info, Gio.FILE_ATTRIBUTE_OWNER_USER),
        group=_str_of(info, Gio.FILE_ATTRIBUTE_OWNER_GROUP),
        content_type=_str_of(info, "standard::content-type"),
        symlink_target=_str_of(info, Gio.FILE_ATTRIBUTE_STANDARD_SYMLINK_TARGET),
        trashed=bool(info.get_attribute_boolean("trashed::deleted")),
    )


def list_dir(path: str, show_hidden: bool = True) -> list[FileEntry]:
    """Synchronously enumerate ``path`` into a list of :class:`FileEntry`.

    ``path`` may be a real filesystem path or the virtual ``trash://`` location.

    Raises :class:`Gio.Error` on permission problems; callers should present a
    friendly dialog.
    """
    if is_trash(path):
        return list_trash()
    parent = Gio.File.new_for_path(path)
    enumerator = parent.enumerate_children(_ATTRS, Gio.FileQueryInfoFlags.NONE)
    try:
        entries: list[FileEntry] = []
        for info in enumerator:
            entry = _entry_from_info(path, info)
            if not show_hidden and entry.is_hidden:
                continue
            if entry.name in (".", ".."):
                continue
            entries.append(entry)
        return entries
    finally:
        enumerator.close()


# --- Trash (like the Windows Recycle Bin) -----------------------------------

_TRASH_ATTRS = (
    Gio.FILE_ATTRIBUTE_STANDARD_NAME + "," +
    Gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME + "," +
    Gio.FILE_ATTRIBUTE_STANDARD_TYPE + "," +
    Gio.FILE_ATTRIBUTE_STANDARD_SIZE + "," +
    Gio.FILE_ATTRIBUTE_TIME_MODIFIED + "," +
    "trashed::orig-path" + "," +
    "trashed::deletion-date" +
    ""
)


def list_trash() -> list[FileEntry]:
    """Enumerate the user's Trash. Each entry carries its ``trash://`` uri in
    ``path``/``uri`` and the original location in ``orig_path``.

    Returns ``[]`` when the platform/desktop has no Trash support rather than
    raising, so the Trash view degrades gracefully.
    """
    base = Gio.File.new_for_uri(TRASH_URI)
    try:
        enumerator = base.enumerate_children(_TRASH_ATTRS,
                                             Gio.FileQueryInfoFlags.NONE)
    except Exception:  # noqa: BLE001 - no trash support (e.g. containers/CLI)
        return []
    try:
        out: list[FileEntry] = []
        for info in enumerator:
            name = info.get_name()
            child = base.get_child(name)
            uri = child.get_uri()
            out.append(
                FileEntry(
                    name=name,
                    display_name=info.get_display_name(),
                    path=uri,
                    uri=uri,
                    is_dir=info.get_file_type() == Gio.FileType.DIRECTORY,
                    is_symlink=False,
                    is_hidden=False,
                    size=info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_STANDARD_SIZE),
                    mtime=int(info.get_attribute_uint64(
                        Gio.FILE_ATTRIBUTE_TIME_MODIFIED)) or 0,
                    mode=0,
                    uid=0,
                    gid=0,
                    owner="",
                    group="",
                    content_type=info.get_content_type() or "",
                    symlink_target="",
                    trashed=True,
                    orig_path=info.get_attribute_string("trashed::orig-path") or "",
                )
            )
        return out
    finally:
        enumerator.close()


def entry_for_uri(uri: str) -> FileEntry:
    """Fetch a single :class:`FileEntry` for a ``trash://`` item."""
    base = Gio.File.new_for_uri(TRASH_URI)
    child = Gio.File.new_for_uri(uri)
    info = child.query_info(_TRASH_ATTRS, Gio.FileQueryInfoFlags.NONE)
    name = info.get_name()
    return FileEntry(
        name=name,
        display_name=info.get_display_name(),
        path=uri,
        uri=uri,
        is_dir=info.get_file_type() == Gio.FileType.DIRECTORY,
        is_symlink=False,
        is_hidden=False,
        size=info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_STANDARD_SIZE),
        mtime=int(info.get_attribute_uint64(Gio.FILE_ATTRIBUTE_TIME_MODIFIED)) or 0,
        mode=0, uid=0, gid=0, owner="", group="",
        content_type=info.get_content_type() or "",
        symlink_target="",
        trashed=True,
        orig_path=info.get_attribute_string("trashed::orig-path") or "",
    )


def restore(uri: str) -> bool:
    """Restore a trashed item back to its original location."""
    return Gio.File.new_for_uri(uri).untrash(None)


def trash_delete(uri: str) -> None:
    """Permanently delete a single trashed item."""
    Gio.File.new_for_uri(uri).delete(None)


def empty_trash() -> tuple[int, list[str]]:
    """Permanently delete every item in the Trash.

    Returns ``(ok_count, errors)``; ``errors`` are per-item messages.
    """
    base = Gio.File.new_for_uri(TRASH_URI)
    enumerator = base.enumerate_children(
        Gio.FILE_ATTRIBUTE_STANDARD_NAME, Gio.FileQueryInfoFlags.NONE)
    try:
        errors: list[str] = []
        ok = 0
        for info in enumerator:
            child = base.get_child(info.get_name())
            try:
                child.delete(None)
                ok += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{info.get_name()}: {exc}")
        return ok, errors
    finally:
        enumerator.close()


def entry_for_path(path: str) -> FileEntry:
    return _entry_from_info(
        os.path.dirname(path.rstrip(os.sep)) or "",
        Gio.File.new_for_path(path).query_info(
            _ATTRS, Gio.FileQueryInfoFlags.NONE
        ),
    )


def rename(src_path: str, new_path: str) -> None:
    Gio.File.new_for_path(src_path).set_display_name(os.path.basename(new_path))


def make_directory(path: str) -> None:
    Gio.File.new_for_path(path).make_directory(None)


def make_file(path: str) -> None:
    Gio.File.new_for_path(path).create(Gio.FileCreateFlags.NONE)


def copy(src: str, dst: str, *, overwrite: bool = False) -> bool:
    flags = Gio.FileCopyFlags.OVERWRITE if overwrite else Gio.FileCopyFlags.NONE
    return Gio.File.new_for_path(src).copy(
        Gio.File.new_for_path(dst), flags, None, None, None
    )


def move(src: str, dst: str, *, overwrite: bool = False) -> bool:
    flags = Gio.FileCopyFlags.OVERWRITE if overwrite else Gio.FileCopyFlags.NONE
    return Gio.File.new_for_path(src).move(
        Gio.File.new_for_path(dst), flags, None, None, None
    )


def delete_permanent(path: str) -> None:
    Gio.File.new_for_path(path).delete(None)


def trash(path: str) -> bool:
    return Gio.File.new_for_path(path).trash(None)


def set_permissions(path: str, mode: int) -> None:
    Gio.File.new_for_path(path).set_attribute_uint32(
        "unix::mode", mode
    )


def set_owner(path: str, uid: int | None = None, gid: int | None = None) -> None:
    f = Gio.File.new_for_path(path)
    if uid is not None:
        f.set_attribute_uint32("unix::uid", uid)
    if gid is not None:
        f.set_attribute_uint32("unix::gid", gid)


def is_writable(path: str) -> bool:
    """Best-effort writability check for a path (does not raise)."""
    try:
        return os.access(path, os.W_OK)
    except OSError:
        return False


def is_readable(path: str) -> bool:
    try:
        return os.access(path, os.R_OK)
    except OSError:
        return False


def free_space(path: str) -> int:
    """Return free bytes on the file system that holds ``path``."""
    result = os.statvfs(path)
    return int(result.f_bavail * result.f_frsize)


def unique_path(path: str) -> str:
    """Return ``path`` or a ``n (copy)`` suffixed path that does not exist."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    for i in range(1, 10000):
        candidate = f"{base} (copy {i}){ext}"
        if not os.path.exists(candidate):
            return candidate
    raise RuntimeError("could not find a free name")


def resolve_symlink(path: str) -> str:
    return os.path.realpath(path)
