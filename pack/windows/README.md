# Windows packaging (MSYS2 + PyInstaller)

RibbonFM uses GTK3 via PyGObject. On Windows the cleanest way to bundle GTK is the
**MSYS2** distribution, which ships a mingw64 GTK3 + Python build, then package
with **PyInstaller** (or simply ship the venv).

## TL;DR

1. Install MSYS2 from <https://www.msys2.org/>.
2. Open the **MSYS2 UCRT64/MINGW64** shell and install the toolchain:

   ```sh
   pacman -S --needed base-devel mingw-w64-ucrt-x86_64-gtk3 \
       mingw-w64-ucrt-x86_64-python mingw-w64-ucrt-x86_64-python-pip \
       mingw-w64-ucrt-x86_64-gobject-introspection mingw-w64-ucrt-x86_64-python-gobject
   ```

3. Install the project and PyInstaller:

   ```sh
   python -m venv .venv
   source .venv/Scripts/activate
   pip install -e . pyinstaller
   ```

4. Build:

   ```sh
   pyinstaller pack/windows/ribbonfm.spec
   ```

   The binary appears in `dist/RibbonFM/`. Copy the MSYS2 `mingw64` runtime folder
   (the RT DLLs, the `lib/girepository-1.0`, `lib/gtk-3.0`, `share` icon themes)
   next to it, **or** run the app from within the MSYS2 shell so the runtime is
   found on `PATH`.

> GTK needs its runtime data on `PATH`/`GI_TYPELIB_PATH`. For a self-contained
> folder use `gdk-pixbuf-query-loaders --update-cache` and copy the whole
> `mingw64/{bin,lib,share}` tree. See the GTK-on-Windows docs.

## UAC elevation

The application **never runs as administrator**. Actions that need elevation
(e.g. writing to `Program Files` or `C:\Windows`) are delegated to the helper
under `pack/windows/runas_helper.py`, which is launched with the `runas` verb:

```python
import ctypes, os, sys
from subprocess import Popen

def elevate(args):
    # ShellExecuteW with 'runas' shows the UAC prompt.
    r = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(args), None, 1)
    if r <= 32:
        raise OSError(f"elevation failed ({r})")
```

The helper performs a single, well-defined privileged action using the validated
path passed on the command line. It exits immediately without keeping privileges.
