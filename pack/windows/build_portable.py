#!/usr/bin/env python3
"""Build a portable, no-install Windows ZIP of RibbonFM.

Approach: MSYS2's mingw-w64 Python + PyGObject are installed via pacman and
there is **no pip** (and no PyPI wheels for ucrt64), so PyInstaller/pip packaging
does not apply here. Instead we bundle a trimmed MSYS2 runtime *plus* the app
and a launcher, producing a self-contained folder you can unzip and run.

The runtime directories (``bin``, ``lib``, ``share``) are copied from the active
mingw64 prefix (``MINGW_PREFIX`` / ``/mingw64`` / ``C:/msys64/mingw64``). The
launcher sets the environment (PATH, PYTHONPATH, GI_TYPELIB_PATH,
GTK_DATA_PREFIX, XDG_DATA_DIRS, gdk-pixbuf loaders) and runs the bundled Python.

Run in an MSYS2/mingw64 shell:
    python pack/windows/build_portable.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "src" / "ribbonfm"


def version() -> str:
    """Version for filenames, from the release tag if present.

    Prefers ``GITHUB_REF_NAME`` (``v1.8`` -> ``1.8``) which is set by GitHub
    Actions for the released tag; ``git describe --tags`` works too but needs
    tags fetched by the checkout step (default checkout only fetches the commit).
    """
    ref = os.environ.get("GITHUB_REF_NAME", "")
    if ref.startswith("v"):
        return ref[1:]
    try:
        tag = subprocess.run(
            ["git", "-C", str(ROOT), "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, check=True).stdout.strip()
        return tag[1:] if tag.startswith("v") else tag
    except Exception:
        return "0.1.0"


def mingw_prefix() -> Path:
    env = os.environ.get("MINGW_PREFIX")
    if env:
        return Path(env)
    for cand in ("/mingw64", "C:/msys64/mingw64", "C:\\msys64\\mingw64"):
        p = Path(cand)
        if p.is_dir():
            return p
    raise SystemExit("mingw64 prefix not found; run inside an MSYS2/mingw64 shell")


def copy_runtime(prefix: Path, stage: Path) -> None:
    """Copy the MSYS2 runtime pieces required to run GTK3 + PyGObject."""
    for sub in ("bin", "lib", "share"):
        src = prefix / sub
        if not src.is_dir():
            continue
        dst = stage / "runtime" / sub
        print(f"  copying {sub}/ ...")
        shutil.copytree(src, dst, dirs_exist_ok=True)


def write_launcher(stage: Path) -> None:
    bat = stage / "RibbonFM.bat"
    bat.write_text(
        "@echo off\r\n"
        "setlocal\r\n"
        "set \"H=%~dp0\"\r\n"
        'set "PATH=%H%runtime\\bin;%PATH%"\r\n'
        'set "PYTHONPATH=%H%app"\r\n'
        'set "GI_TYPELIB_PATH=%H%runtime\\lib\\girepository-1.0"\r\n'
        'set "GTK_EXE_PREFIX=%H%runtime"\r\n'
        'set "GTK_DATA_PREFIX=%H%runtime"\r\n'
        'set "XDG_DATA_DIRS=%H%runtime\\share"\r\n'
        'set "GDK_PIXBUF_MODULE_FILE=%H%runtime\\lib\\gdk-pixbuf-2.0\\2.10.0\\loaders.cache"\r\n'
        'set "GIO_MODULE_DIR=%H%runtime\\lib\\gio\\modules"\r\n'
        'set "FONTCONFIG_PATH=%H%runtime\\etc\\fonts"\r\n'
        'set "FONTCONFIG_FILE=%H%runtime\\etc\\fonts\\fonts.conf"\r\n'
        '"%H%runtime\\bin\\python.exe" -m ribbonfm %*\r\n'
        "endlocal\r\n",
        encoding="utf-8")


def make_zip(stage: Path) -> Path:
    out = ROOT / "dist" / f"RibbonFM-{version()}-windows-x86_64-portable.zip"
    print(f"Zipping to {out}")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(stage))
    return out


def main() -> int:
    print("== portable bundle (MSYS2 runtime, no pip/PyInstaller) ==")
    prefix = mingw_prefix()
    print("mingw prefix:", prefix)
    stage = ROOT / "build" / "winportable"
    app_dst = stage / "app" / "ribbonfm"
    shutil.rmtree(app_dst, ignore_errors=True)
    shutil.copytree(APP, app_dst)
    # Emit the version inside the bundled app (not in the source tree).
    (app_dst / "_version.py").write_text(f'__version__ = "{version()}"\n',
                                         encoding="utf-8")
    copy_runtime(prefix, stage)
    write_launcher(stage)

    out = make_zip(stage)
    print(f"DONE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
