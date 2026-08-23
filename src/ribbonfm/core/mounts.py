"""Volume, drive and mount point discovery through Gio.VolumeMonitor."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Optional

from gi.repository import Gio

from . import pathutils


@dataclass(frozen=True)
class MountInfo:
    """A single disk volume, mounted or not."""

    name: str
    path: Optional[str]      # mount root path, None when not mounted
    uri: str                 # classic identifier (unique per volume)
    icon_name: str
    is_removable: bool
    has_volume: bool
    volume: object           # the underlying Gio.Volume (may be None)
    mounted: bool

    @property
    def is_valid(self) -> bool:
        return bool(self.path)


def list_mounts() -> list[MountInfo]:
    """Return **all** disk volumes (mounted and unmounted) for the sidebar.

    Mounted ones carry a usable ``path``; unmounted ones can be mounted by
    :func:`mount_volume`.
    """
    monitor = Gio.VolumeMonitor.get()
    found: list[MountInfo] = []
    seen: set[str] = set()

    for volume in monitor.get_volumes():
        if volume is None:
            continue
        mount = volume.get_mount()
        path = None
        uri = volume.get_identifier("classic") or ""
        if mount is not None:
            root = mount.get_root()
            path = root.get_path()
            uri = root.get_uri()
        key = uri or (path or "") or str(id(volume))
        if key in seen:
            continue
        seen.add(key)
        icon_name = "drive-harddisk"
        try:
            icon = volume.get_icon()
            names = icon.get_names() if hasattr(icon, "get_names") else []
            if names:
                icon_name = names[0]
        except Exception:
            pass
        found.append(
            MountInfo(
                name=volume.get_name(),
                path=path,
                uri=uri,
                icon_name=icon_name,
                is_removable=_removable(volume.get_drive()),
                has_volume=True,
                volume=volume,
                mounted=bool(mount),
            )
        )

    # Fall back to real mount points (e.g. containers/minimal environments
    # where Gio.VolumeMonitor reports no volumes) so the sidebar always shows
    # actual disks.
    for mp in _os_mount_points():
        if mp in seen:
            continue
        seen.add(mp)
        found.append(
            MountInfo(
                name=os.path.basename(mp) or mp,
                path=mp,
                uri="",
                icon_name="drive-harddisk",
                is_removable=False,
                has_volume=False,
                volume=None,
                mounted=True,
            )
        )
    return found


def _os_mount_points() -> list[str]:
    """Real mount points from /proc/mounts, excluding pseudo filesystems."""
    if not pathutils.IS_LINUX:
        return []
    skip = {
        "proc", "sysfs", "devpts", "cgroup", "cgroup2", "pstore", "securityfs",
        "debugfs", "tracefs", "configfs", "fusectl", "mqueue", "hugetlbfs",
        "binfmt_misc", "rpc_pipefs", "devtmpfs", "bpf", "autofs", "squashfs",
    }
    out: list[str] = []
    try:
        with open("/proc/mounts", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) < 3:
                    continue
                mp, fstype = parts[1], parts[2]
                if fstype in skip:
                    continue
                if mp.startswith(("/proc", "/sys", "/dev", "/run")) and \
                        fstype in ("tmpfs", "devtmpfs", "ramfs"):
                    continue
                out.append(mp)
    except OSError:
        pass
    return out


def mount_volume(info: MountInfo, on_done: Callable[[str, str], None]) -> None:
    """Mount an unmounted volume, then deliver ``(path, error)``.

    ``path`` is the mount root path or ``""``; ``error`` is a translated message
    or ``""`` on success. The callback runs on the GTK main loop.
    """
    volume = info.volume
    if volume is None:
        on_done("", "No volume available.")
        return
    if info.mounted and info.path:
        on_done(info.path, "")
        return

    def _cb(volume_, result, _ud):
        path = ""
        error = ""
        try:
            if not volume_.get_mount():
                volume_.mount_finish(result)
            m = volume_.get_mount()
            path = m.get_root().get_path() or "" if m else ""
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        on_done(path, error)

    volume.mount(Gio.MountMountFlags.NONE, None, None, _cb)


def _removable(drive) -> bool:
    if drive is None:
        return False
    try:
        return bool(drive.is_removable())
    except Exception:
        return False


def is_mount_point(path: str) -> bool:
    """Check if ``path`` is a mount point (best effort on unix)."""
    if not pathutils.IS_LINUX and not pathutils.IS_MACOS:
        return False
    import os

    try:
        before = os.stat(path)
        after = os.stat(os.path.dirname(path.rstrip(os.sep)) or "/")
        if before.st_dev != after.st_dev:
            return True
        return False
    except OSError:
        return False
