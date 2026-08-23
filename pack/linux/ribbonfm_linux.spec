# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a fully self-contained Linux build.

Bundles GTK3 + PyGObject (via the contributed hooks) and the application
resources (Glade UI, CSS, compiled .mo catalogs), producing a onedir ``RibbonFM``
folder that runs without any system GTK/PyGObject dependency.
"""

from PyInstaller.utils.hooks import collect_all, collect_data_files

datas, binaries, hiddenimports = [], [], []

# PyGObject / GTK bindings.
for pkg in ("gi", "pygtkcompat", "cairo"):
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
    ["pack/linux/launcher.py"],
    pathex=[],
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
    upx=False,
    console=False,
)

coll = COLLECT(exe, a.binaries, a.datas, name="RibbonFM")
