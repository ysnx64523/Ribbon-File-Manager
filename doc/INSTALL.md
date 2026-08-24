# Installation

RibbonFM is a GTK3 (PyGObject) application. The GTK shared libraries are **system**
packages (PyGObject is not reliably pip-installable everywhere), so the recommended
path is to install the runtime through your package manager and then install this
project into a virtual environment. Prebuilt packages below also bundle the
runtime for a fully self-contained install.

## Python version

RibbonFM is built and tested on **Python 3.14** (GTK3 3.24 + PyGObject) and runs
on Python 3.8+ wherever a matching PyGObject is available (`pyproject.toml`).

## Linux (Debian/Ubuntu/Fedora/Arch)

```sh
# 1. System runtime (GTK3 + PyGObject)
# Debian/Ubuntu:
sudo apt install python3-gi gir1.2-gtk-3.0 libgtk-3-0 adwaita-icon-theme
# Fedora:
#   sudo dnf install python3-gobject gtk3
# Arch:
#   sudo pacman -S python-gobject gtk3

# 2. Virtual environment (system site packages => gi from the distro)
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e . pytest

# 3. Build the translation catalogs
python tools/gen_po.py

# 4. Run
ribbonfm
# or
python -m ribbonfm
```

> Use `--system-site-packages` so the venv can see the distribution's GTK
> bindings (`gi`). If you prefer an isolated venv, install PyGObject for your
> interpreter first.

## Linux packages (choose one)

### .deb (self-contained)

Builds a `.deb` that **bundles GTK/PyGObject** (no system `python3-gi` needed):

```sh
bash pack/linux/build_deb.sh          # -> build/deb/RibbonFM_<version>_amd64.deb
sudo dpkg -i build/deb/RibbonFM_*_amd64.deb
ribbonfm
```

### AppImage (self-contained)

```sh
bash pack/appimage/build.sh           # -> dist/RibbonFileManager-*-x86_64.AppImage
./dist/RibbonFileManager-*-x86_64.AppImage
```

### Flatpak

```sh
flatpak-builder --install --user --force-clean build-flatpak \
    pack/flatpak/org.ribbonfm.RibbonFM.json
flatpak run org.ribbonfm.RibbonFM
```

## Windows

See [`pack/windows/README.md`](pack/windows/README.md) (MSYS2 + PyInstaller).
Build a **portable, no-installer ZIP** that bundles the runtime:

```sh
python pack/windows/build_portable.py # -> dist/RibbonFM-*-windows-x86_64-portable.zip
```

## macOS

See [`pack/macos/README.md`](pack/macos/README.md) (Homebrew + py2app).

## Running from a source checkout without installing

```sh
export PYTHONPATH=src
python -m ribbonfm --lang zh-CN
```

## Testing

```sh
python -m unittest discover -s tests -v
```

Core tests only require `gi` (Gio/GLib) and no display. CI runs them on the
system python3 after `sudo apt install python3-gi`.

## Translation

The catalog is generated from the source (auto-creating the `.pot` if missing —
e.g. in CI) and merged with the translations in `tools/gen_po.py`:

```sh
python tools/gen_po.py      # writes po/<lang>.po and compiles .mo into resources/locale/
```

To add a language, append its dictionary to `TRANSLATIONS` in `tools/gen_po.py`
and rebuild (uses `xgettext`/`msgfmt`; `gettext` required).
