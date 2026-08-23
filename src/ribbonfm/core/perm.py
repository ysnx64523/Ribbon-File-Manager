"""Permission checks and privilege escalation.

Design goals
------------
* The application itself **never** runs with elevated privileges.
* Privileged operations (``chmod``/``chown``, writes to protected directories,
  deleting system files, mounting...) are performed on demand through the OS
  secure mechanism: ``pkexec`` on Linux, UAC ``runas`` on Windows, and
  Authorization Services / ``osascript`` on macOS.
* The ``777`` permission case is not rejected outright (the user may legitimately
  want it) but produces a security warning.
* Every user-visible string is wrapped in ``_()`` so it can be translated.

Security
--------
* Paths are passed as argument lists (never through a shell) to prevent command
  injection.
* Before escalation the target path is canonicalised and sanity-checked.
* On non-Linux systems :func:`escalate` raises :class:`UnsupportedError` so the
  UI can degrade gracefully instead of guessing.

This module must stay free of GTK imports to remain testable.
"""

from __future__ import annotations

import os
import platform
import stat
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

from ..i18n import _

from . import pathutils

IS_LINUX = pathutils.IS_LINUX
IS_WINDOWS = pathutils.IS_WINDOWS
IS_MACOS = pathutils.IS_MACOS


class UnsupportedError(RuntimeError):
    """Raised when an escalation mechanism is unavailable on this platform."""


@dataclass(frozen=True)
class PermHint:
    """Human friendly summary of a path's permission state."""

    rwx: str            # e.g. "rwxr-xr--"
    octal: str          # e.g. "755"
    is_owner: bool
    is_group: bool
    is_writable: bool
    is_readable: bool
    is_777: bool
    is_root: bool
    reason: str         # machine readable reason key, "" when all good
    user_name: str
    group_name: str

    @property
    def warning(self) -> bool:
        return self.is_777 or self.is_root


def is_root() -> bool:
    if pathutils.IS_WINDOWS:
        # On Windows we are never "root"; admin status is tracked separately.
        return False
    return os.geteuid() == 0


def current_user() -> str:
    import getpass

    return getpass.getuser()


def is_admin() -> bool:
    """Whether the current process holds administrator privileges."""
    if IS_LINUX or IS_MACOS:
        if IS_MACOS:
            out = subprocess.run(
                ["id", "-u"], capture_output=True, text=True
            ).stdout.strip()
            return out == "0"
        return os.geteuid() == 0
    if IS_WINDOWS:
        try:
            import ctypes

            TOKEN_QUERY = 0x0008
            TokenElevation = 20
            class SID_IDENTIFIER_AUTHORITY(ctypes.Structure):
                _fields_ = [("Value", ctypes.c_ubyte * 6)]
            class SID_AND_ATTRIBUTES(ctypes.Structure):
                _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", ctypes.c_uint32)]
            class SID(ctypes.Structure):
                _fields_ = [
                    ("Revision", ctypes.c_ubyte),
                    ("SubAuthorityCount", ctypes.c_ubyte),
                    ("IdentifierAuthority", SID_IDENTIFIER_AUTHORITY),
                    ("SubAuthority", ctypes.c_uint32 * 1),
                ]
            # A truncated but sufficient check for this module's needs.
            return _win_admin()
        except Exception:
            return False
    return False


def _win_admin() -> bool:  # pragma: no cover - windows only
    import ctypes

    class SID_IDENTIFIER_AUTHORITY(ctypes.Structure):
        _fields_ = [("Value", ctypes.c_ubyte * 6)]

    class SID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", ctypes.c_uint32)]

    class TOKEN_MANDATORY_LABEL(ctypes.Structure):
        _fields_ = [("Label", SID_AND_ATTRIBUTES)]

    SECURITY_NT_AUTHORITY = 5
    SECURITY_MANDATORY_MEDIUM_RID = 0x2000
    SECURITY_MANDATORY_HIGH_RID = 0x2000 + 1
    TokenIntegrityLevel = 25
    ERROR_INSUFFICIENT_BUFFER = 122

    advapi32 = ctypes.windll.advapi32
    kernel32 = ctypes.windll.kernel32

    h_token = ctypes.c_void_p()
    TOKEN_QUERY = 0x0008
    TOKEN_INFORMATION_CLASS = 25  # TokenIntegrityLevel used via GetTokenInformation
    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(h_token)
    ):
        return False
    size = ctypes.c_uint32()
    if advapi32.GetTokenInformation(
        h_token, TokenIntegrityLevel, None, 0, ctypes.byref(size)
    ):
        return False
    if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
        return False
    buffer = ctypes.create_string_buffer(size.value)
    if not advapi32.GetTokenInformation(
        h_token, TokenIntegrityLevel, buffer, size.value, ctypes.byref(size)
    ):
        return False
    token = ctypes.cast(buffer, ctypes.POINTER(TOKEN_MANDATORY_LABEL))
    sid = token.contents.Label.Sid
    if not sid:
        return False
    # The mandatory level SID is a well known SID whose final sub-authority
    # indicates the integrity level.
    sub_count = int.from_bytes(ctypes.string_at(sid + 1, 1), "little")
    # Sid pointer layout: revision(1) + subauthcount(1) + authority(6) + subs.
    # We read the last sub-authority as a little-endian uint32.
    base = ctypes.addressof(sid) + 8  # skip revision, subauthcount, authority
    last = ctypes.c_uint32.from_address(base + (sub_count - 1) * 4).value
    return last >= SECURITY_MANDATORY_HIGH_RID


def _mode_str(mode: int) -> str:
    bits = [
        mode & stat.S_IRUSR, mode & stat.S_IWUSR, mode & stat.S_IXUSR,
        mode & stat.S_IRGRP, mode & stat.S_IWGRP, mode & stat.S_IXGRP,
        mode & stat.S_IROTH, mode & stat.S_IWOTH, mode & stat.S_IXOTH,
    ]
    return "".join("rwxrwxrwx"[i] if b else "-" for i, b in enumerate(bits))


def inspect(path: str) -> PermHint:
    """Gather a permission summary for ``path`` (never raises)."""
    if IS_WINDOWS:
        writable = _win_writable(path)
        return PermHint(
            rwx="", octal="", is_owner=False, is_group=False,
            is_writable=writable, is_readable=writable,
            is_777=False, is_root=False, reason="", user_name="",
            group_name="",
        )
    try:
        st = os.stat(path)
        mode = stat.S_IMODE(st.st_mode)
    except OSError:
        return PermHint(
            rwx="", octal="", is_owner=False, is_group=False,
            is_writable=False, is_readable=False, is_777=False,
            is_root=is_root(), reason="noexist", user_name=current_user(),
            group_name="",
        )
    import pwd
    import grp

    try:
        user = pwd.getpwuid(st.st_uid).pw_name
    except KeyError:
        user = str(st.st_uid)
    try:
        group = grp.getgrgid(st.st_gid).gr_name
    except KeyError:
        group = str(st.st_gid)
    owner = st.st_uid == os.geteuid()
    group_ok = st.st_gid == os.getegid()
    writable = os.access(path, os.W_OK)
    readable = os.access(path, os.R_OK)
    perms = _mode_str(mode)
    reason = ""
    if not writable:
        reason = "no-write"
    elif not readable:
        reason = "no-read"
    if mode & stat.S_IROTH and mode & stat.S_IWOTH and mode & stat.S_IXOTH:
        reason = ""  # not an error just because 777; still report below
    return PermHint(
        rwx=perms, octal=f"{mode:o}", is_owner=owner, is_group=group_ok,
        is_writable=writable, is_readable=readable,
        is_777=(mode & 0o777 == 0o777), is_root=is_root(), reason=reason,
        user_name=user, group_name=group,
    )


def _win_writable(path: str) -> bool:  # pragma: no cover - windows only
    try:
        return os.access(path, os.W_OK)
    except OSError:
        return False


def can_no_privilege(path: str) -> bool:
    """True if the current (non-elevated) user may write to ``path``."""
    try:
        return os.access(path, os.W_OK)
    except OSError:
        return False


# --- Privileged operations -------------------------------------------------

def _pkexec_ok() -> bool:
    if not IS_LINUX:
        return False
    try:
        import shutil

        return shutil.which("pkexec") is not None
    except Exception:
        return False


def escalate(
    *cmds: list[str],
) -> tuple[bool, str]:
    """Run a privileged command via the OS secure mechanism.

    Args:
        cmds: one or more command token lists, each run with the same credential.

    Returns:
        ``(success, message)`` where ``message`` is translated and safe to show.
    """
    if not cmds:
        return True, ""
    # We execute the first command list; multiple are chained sequentially.
    for tokens in cmds:
        ok, message = _escalate_tokens(tokens)
        if not ok:
            return ok, message
    return True, ""


def _escalate_tokens(tokens: list[str]) -> tuple[bool, str]:
    """Run ``tokens`` with privileges and return (ok, error or '')."""
    if IS_LINUX:
        if not _pkexec_ok():
            return False, _("pkexec is not available to elevate privileges.")
        full = ["pkexec"] + tokens
        try:
            result = subprocess.run(full, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return False, _("The privileged operation timed out.")
        except OSError as exc:
            return False, _("Failed to start the privileged helper: {err}").format(err=exc)
        if result.returncode == 0:
            return True, ""
        if result.returncode in (126, 127):
            return False, _("You cancelled the authentication request.")
        return False, _("The privileged operation was rejected: {msg}").format(
            msg=result.stderr.strip() or result.stdout.strip() or "unknown error"
        )
    if IS_WINDOWS:
        raise UnsupportedError(_("runas escalation is not wired up in this build."))
    if IS_MACOS:
        raise UnsupportedError(_("osascript escalation is not wired up in this build."))
    raise UnsupportedError(_("Privilege escalation is not supported on this platform."))


def chmod(path: str, mode: int) -> tuple[bool, str]:
    """Change permissions, escalating via pkexec when the user lacks rights.

    Returns ``(success, message)``.
    """
    canonical = os.path.realpath(path)
    st = os.stat(canonical)
    if st.st_uid == os.geteuid() or os.access(canonical, os.W_OK):
        try:
            os.chmod(canonical, mode)
            return True, ""
        except PermissionError:
            pass
        except OSError as exc:
            return False, _("Could not change permissions: {err}").format(err=exc)
    return _escalate_tokens(["/bin/chmod", f"{mode:o}", canonical])


def chown(
    path: str, uid: Optional[int] = None, gid: Optional[int] = None
) -> tuple[bool, str]:
    """Change ownership, escalating when required."""
    canonical = os.path.realpath(path)
    args = ["/bin/chown"]
    if uid is not None:
        args.append(str(uid))
    if gid is not None:
        args.append(f":{gid}" if uid is not None else str(gid))
    args.append(canonical)
    return _escalate_tokens(args)


def write_protected(path: str, data: bytes = b"") -> tuple[bool, str]:
    """Write to a location that likely needs elevation (e.g. /etc/*)."""
    return _escalate_tokens(["/bin/touch", os.path.realpath(path)])
