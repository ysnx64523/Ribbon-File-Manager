# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for RibbonFM on Windows (built in an MSYS2/mingw64 shell).
#
# Build:
#   pyinstaller pack/windows/ribbonfm.spec
#
# Notes:
#   - GTK3 must be installed in the MSYS2 mingw64 environment.
#   - PyGObject needs the PyGObject "hooks" from pyinstaller-hooks-contrib;
#     these are pulled in automatically for gi/Gtk when using the official
#     PyGObject binary packages.
#   - Because the app never runs elevated, the auxiliary privileged helper
#     (see pack/windows/runas_helper.py) must be built/placed on PATH or it is
#     simply not present (the app degrades gracefully).

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []

# Pull in GTK/PyGObject data and binaries.
for pkg in ("gi", "pygtkcompat"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# On Windows GIO ships a large set of modules; include them.
hiddenimports += [
    "gi.overrides",
    "gi.overrides.Gtk",
    "gi.overrides.Gio",
    "gi.overrides.Pango",
    "gi.overrides.GdkPixbuf",
    "gi.repository.Gtk",
    "gi.repository.Gio",
    "gi.repository.Gdk",
    "gi.repository.Pango",
    "gi.repository.GdkPixbuf",
    "gi.repository.GLib",
    "gi.repository.GObject",
]

a = Analysis(
    ["../src/ribbonfm/app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RibbonFM",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
