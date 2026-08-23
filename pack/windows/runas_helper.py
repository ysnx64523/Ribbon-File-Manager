#!/usr/bin/env python3
"""Privileged helper for Windows (run via UAC ``runas``).

This helper is intentionally tiny: it performs ONE well defined action, on a
path that the caller supplies, then exits immediately. **It must never be
run for interactive operations**. The main application launches it with
``ShellExecuteW(..., "runas", ...)`` which triggers the UAC prompt.

Supported commands (arguments after ``--``)::

    chmod <mod_str> <path>
    chown <path> <uid|owner> [gid|group]
    write <path>             # touch-like privileged write

Exit codes: 0 on success, non-zero on failure. Errors are printed to stderr.
"""

import os
import sys
import stat


def chmod(args: list[str]) -> int:
    if len(args) != 2:
        return 2
    mode_str, path = args
    try:
        mode = int(mode_str, 8)
    except ValueError:
        return 3
    try:
        os.chmod(path, mode)
    except OSError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def chown(args: list[str]) -> int:
    if len(args) not in (2, 3):
        return 2
    path = args[0]
    uid = _parse_uid(args[1])
    gid = _parse_uid(args[2]) if len(args) > 2 else None
    try:
        if uid is not None:
            os.chown(path, uid, -1)
        if gid is not None:
            os.chown(path, -1, gid)
    except OSError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def _parse_uid(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def write(args: list[str]) -> int:
    if len(args) != 1:
        return 2
    path = args[0]
    try:
        with open(path, "a"):
            pass
    except OSError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        return 2
    cmd = argv[0]
    args = argv[1:]
    handlers = {"chmod": chmod, "chown": chown, "write": write}
    func = handlers.get(cmd)
    if func is None:
        return 2
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
