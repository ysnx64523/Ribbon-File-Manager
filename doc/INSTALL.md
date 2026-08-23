# Installation

RibbonFM is a GTK3 (PyGObject) application. The GTK shared libraries are **system**
packages (PyGObject is not reliably pip-installable everywhere), so the recommended
path is to install the runtime through your package manager and then install this
project into a virtual environment.

## Python version

RibbonFM supports Python **3.8 and newer**. GTK3 (3.24) + PyGObject are required.

## Linux (Debian/Ubuntu/Fedora/Arch)

```sh
# 1. System runtime (GTK3 + PyGObject)
# Debian/Ubuntu:
sudo apt install python3-gi gir1.2-gtk-3.0 libgtk-3-0 adwaita-icon-theme
# Fedora:
#   sudo dnf install python3-gobject gtk3
# Arch:
#   sudo pacman -S python-gobject gtk3

# 2. Virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e . pytest

# 3. Build the translation catalogs
python tools/gen_po.py

# 4. Run
ribbonfm
# or
python -m ribbonfm
```

> If `python3` is 3.11+ and your distro ships a matching PyGObject, the venv can
> use the *system site packages* (`python3 -m venv --system-site-packages .venv`)
> so the GTK bindings resolve without installing anything extra.

## Linux (Flatpak)

```sh
flatpak-builder --install --user --force-clean build-flatpak \
    pack/flatpak/org.ribbonfm.RibbonFM.json
flatpak run org.ribbonfm.RibbonFM
```

## Linux (AppImage)

```sh
bash pack/appimage/build.sh
./dist/RibbonFileManager-*-x86_64.AppImage
```

## Windows

See [`pack/windows/README.md`](pack/windows/README.md) (MSYS2 + PyInstaller).

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

## Translation

The catalog is generated from the source and merged with the translations in
`tools/gen_po.py`:

```sh
python tools/gen_po.py      # writes po/<lang>.po and compiles .mo into resources/locale/
```

To add a language, append its dictionary to `TRANSLATIONS` in `tools/gen_po.py`
and rebuild (uses `msgfmt`; `gettext` required).
