#!/usr/bin/env python3
"""Build a portable (no-install) Windows ZIP of RibbonFM.

Runs PyInstaller with :file:`pack/windows/ribbonfm.spec`, then packages the
resulting ``dist/RibbonFM`` folder into a ``.zip``. The GTK runtime is bundled
by PyInstaller's PyGObject hooks; on MSYS2 the runtime libraries are found on
``PATH``. An extra runtime folder can be merged in with ``--gtk-runtime <dir>``.

Usage (from the repository root, in an MSYS2/mingw64 shell)::

    python pack/windows/build_portable.py [--gtk-runtime <mingw64 dir>]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "pack" / "windows" / "ribbonfm.spec"
APP_DIR = ROOT / "dist" / "RibbonFM"


def version() -> str:
    """Version from the git tag (``v1.6`` -> ``1.6``), e.g. for filenames."""
    try:
        import subprocess
        tag = subprocess.run(
            ["git", "-C", str(ROOT), "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, check=True).stdout.strip()
        if tag.startswith("v"):
            tag = tag[1:]
        if tag:
            return tag
    except Exception:
        pass
    return "0.1.0"


def run_pyinstaller() -> None:
    print("Running PyInstaller ...")
    # Emit the version for the packaged app (PyInstaller doesn't run setuptools_scm).
    (ROOT / "src" / "ribbonfm" / "_version.py").write_text(
        f'__version__ = "{version()}"\n', encoding="utf-8")
    subprocess.run([sys.executable, "-m", "PyInstaller", str(SPEC)],
                   cwd=str(ROOT), check=True)


def merge_gtk(runtime: Path) -> None:
    if not runtime.is_dir():
        print(f"GTK runtime dir not found: {runtime}")
        return
    print(f"Merging GTK runtime from {runtime}")
    for sub in ("bin", "lib", "share"):
        src = runtime / sub
        if src.is_dir():
            dst = APP_DIR / sub
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)


def make_zip() -> Path:
    out = ROOT / "dist" / f"RibbonFM-{version()}-windows-x86_64.zip"
    print(f"Zipping to {out}")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(APP_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(APP_DIR))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gtk-runtime", type=Path,
                    help="optional MSYS2 mingw64 dir to merge as the GTK runtime")
    args = ap.parse_args()
    run_pyinstaller()
    if args.gtk_runtime:
        merge_gtk(args.gtk_runtime)
    zip_path = make_zip()
    print(f"DONE: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
