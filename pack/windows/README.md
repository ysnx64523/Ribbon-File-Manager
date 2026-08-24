# Windows packaging (MSYS2 runtime bundle, no pip)

RibbonFM uses GTK3 via PyGObject. On Windows the GTK3 + PyGObject bindings come
from **MSYS2** (pacman packages, e.g. `mingw-w64-ucrt-x86_64-python-gobject`).
MSYS2's Python has **no pip** and PyPI does not provide ucrt64 wheels, so we do
**not** use pip or PyInstaller. Instead we bundle a trimmed MSYS2 runtime plus
the app and a `.bat` launcher into a self-contained portable ZIP.

## Build

```sh
# In an MSYS2/mingw64 shell:
python pack/windows/build_portable.py
# -> dist/RibbonFM-<version>-windows-x86_64-portable.zip
```

The script copies `bin`, `lib`, `share` from the active mingw64 prefix (the
GTK3 runtime, Python, PyGObject typelibs, glib schemas, gdk-pixbuf loaders and
the Adwaita icon theme), adds the app under `app/ribbonfm`, and writes a
`RibbonFM.bat` launcher that sets `PATH`, `PYTHONPATH`, `GI_TYPELIB_PATH`,
`GTK_DATA_PREFIX`, `XDG_DATA_DIRS`, `GIO_MODULE_DIR`, `GDK_PIXBUF_MODULE_FILE`
and the fontconfig paths, then runs `python -m ribbonfm`.

Unzip anywhere and double-click `RibbonFM.bat` (or run it from a terminal).

## Installing the runtime with pacman

Used by the CI `windows` job and by anyone building locally:

```sh
pacman -S --needed mingw-w64-x86_64-gtk3 \
    mingw-w64-x86_64-python \
    mingw-w64-x86_64-python-gobject \
    mingw-w64-x86_64-adwaita-icon-theme \
    mingw-w64-x86_64-gettext
```

`MINGW_PREFIX` (e.g. `/mingw64`) selects the runtime to copy; the script falls
back to `/mingw64` and `C:/msys64/mingw64`.

## Notes / limitations

* The bundle is large (it ships the GTK runtime). It is genuinely portable and
  self-contained — no MSYS2 install needed on the target machine.
* The `ucrt64` target has **no pip**; that is exactly why the
  pip/PyInstaller spec (`pack/windows/ribbonfm.spec`) is *not* used for the
  release bundle. That spec is kept for an environment that does provide a
  pip-capable CPython + PyGObject.
* UAC elevation is delegated via `runas_helper.py` (see `doc/SECURITY.md`).
