# Ribbon File Manager (RibbonFM)

A cross-platform file manager with a **Windows-Explorer-like Ribbon toolbar**,
written in Python with **GTK3 (PyGObject)**. It runs natively on Linux and is
designed to be portable to Windows .

![Languages: en, zh_CN](https://img.shields.io/badge/i18n-en%20%7C%20zh__CN-blue) · License: [Apache-2.0](LICENSE) · UI toolkit: GTK3

> **Python**: built and tested on **Python 3.14** with GTK3 3.24 + PyGObject.
> Also runs on Python 3.8+ (see `pyproject.toml`) wherever a matching PyGObject
> is available for the interpreter.

---

## Features

### Ribbon UI (custom, GTK3)
- Tab strip built from `Gtk.Stack` + `Gtk.StackSwitcher`.
- Tabs: **File** (backstage menu), **Home**, **Share**, **View**, **Manage**.
- Large (icon-over-label) and small (icon-beside-label) buttons in groups.
- Collapse/expand the whole Ribbon with one click; `Ctrl`+scroll zooms the view
  (icon size / layout), like Windows Explorer.
- Quick-access toolbar next to the title.

### Navigation
- Back / Forward / Up / Refresh, **breadcrumb** bar and a toggle to an
  **editable address entry**.
- Sidebar with **Places**, **Bookmarks**, **Devices** (mounts) and a **Network**
  placeholder. Bookmarks persist to `~/.config/ribbonfm/`.

### Views
- Large icons, small icons, list, **details** (name/size/type/mtime/permissions/
  owner/group), thumbnails (icon view).
- Sort by name/size/type/mtime; directories always first.
- Group by type; in-folder search/filter; show hidden files.
- Selection modes: click, rubber-band, **Select All**, **Invert Selection**.

### File operations (with async I/O)
- New folder / new file, cut / copy / paste, rename, **move to Trash**
  (`Gio.File.trash`), permanent delete, properties.
- Open with the default app, or **Open With…** (`Gio.AppInfo`).
- Right-click menus for items and for the folder background.

### Permissions & privilege escalation
- Displays `rwx`, octal mode, owner and group in list/details and properties.
- **Never runs elevated.** Privileged operations (`chmod`/`chown`, protected
  writes) escalate through the OS secure mechanism: `pkexec` (Linux), UAC
  `runas` helper (Windows), Authorization Services (macOS).
- Handles `777` without refusing it, but warns; read-only mounts are detected
  and reported.
- See [`doc/SECURITY.md`](doc/SECURITY.md) for the full model.

### i18n
- Every string through gettext `_()`; ship `en` + `zh_CN`, extensible.
- Runtime language switch (asks to restart) and automatic locale detection.
- Localised numbers, dates and sizes.

## Getting started

```sh
# Linux: install GTK3 + PyGObject (system package), then:
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e . pytest
python tools/gen_po.py          # build translation catalogs
ribbonfm                        # or: python -m ribbonfm
```

`--system-site-packages` is used so the venv can see the distribution's GTK
bindings (`gi`). If you prefer an isolated venv, install PyGObject for your
interpreter first (e.g. `apt install python3-gi`).

See [`doc/INSTALL.md`](doc/INSTALL.md) for Linux/Windows/macOS details and
[`pack/`](pack/) for Flatpak, AppImage, PyInstaller and Homebrew packaging.

## Project layout

```
src/ribbonfm/     application (core/ logic separated from ui/ widgets)
data/             desktop file, icon, AppStream metadata
doc/              install, architecture, security docs
pack/             flatpak, appimage, windows, macos packaging
po/               gettext catalogs + generator (tools/gen_po.py)
tests/            unit tests (no display required)
```

## Testing

```sh
python -m unittest discover -s tests -v
```

## Translations

Add a language to `TRANSLATIONS` in [`tools/gen_po.py`](tools/gen_po.py), then:

```sh
python tools/gen_po.py
```

## License

[Apache License 2.0](LICENSE). GTK3 / PyGObject are LGPL; 
