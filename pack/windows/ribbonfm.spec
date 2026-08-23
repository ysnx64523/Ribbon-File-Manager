# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a portable Windows build (bundles the GTK runtime).

Build with ``pack/windows/build_portable.py`` (MSYS2/mingw64). The GTK runtime is
collected from the PyGObject hooks; the application resources (Glade UI, CSS,
compiled .mo catalogs) are bundled as data.
"""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

# Repo root relative to this spec (SPECPATH == pack/windows).
ROOT = Path(os.path.abspath(os.path.join(SPECPATH, "..", "..")))
SRC = str(ROOT / "src")
sys.path.insert(0, SRC)

datas, binaries, hiddenimports = [], [], []

for pkg in ("gi", "pygtkcompat"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Application data: Glade UI, stylesheets, locale catalogs.
datas += collect_data_files("ribbonfm", includes=["resources/**/*"])

hiddenimports += [
    "gi.overrides", "gi.overrides.Gtk", "gi.overrides.Gio",
    "gi.overrides.Pango", "gi.overrides.GdkPixbuf",
    "gi.repository.Gtk", "gi.repository.Gio", "gi.repository.Gdk",
    "gi.repository.GdkPixbuf", "gi.repository.Pango", "gi.repository.GLib",
    "gi.repository.GObject",
]

a = Analysis(
    [str(ROOT / "pack" / "windows" / "launcher.py")],
    pathex=[SRC],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RibbonFM",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="RibbonFM")
