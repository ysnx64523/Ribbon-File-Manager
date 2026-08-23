# Ribbon File Manager (RibbonFM)

A cross-platform file manager with a **Windows-Explorer-like Ribbon toolbar**,
written in Python with **GTK3 (PyGObject)**. It runs natively on Linux and is
designed to be portable to macOS and Windows.

![i18n: en, zh_CN](https://img.shields.io/badge/i18n-en%20%7C%20zh__CN-blue)
![License: Apache-2.0](LICENSE)
![UI: GTK3](https://img.shields.io/badge/UI-GTK3-blue)

> **Python**: built and tested on **Python 3.14** with GTK3 3.24 + PyGObject.
> Also runs on Python 3.8+ (`pyproject.toml`) wherever a matching PyGObject is
> available for the interpreter.

---

## Features

### Ribbon UI (custom, GTK3)
- Tab strip from `Gtk.Stack` + `Gtk.StackSwitcher`.
- Tabs: **File** (backstage menu), **Home**, **Share**, **View**, **Manage**.
- Large (icon-over-label) and small (icon-beside-label) buttons in groups.
- Collapse/expand the whole Ribbon; **Ctrl + scroll** zooms the view (icon size
  / layout), like Windows Explorer.
- Quick-access toolbar next to the title.

### Navigation
- Back / Forward / Up / Refresh, **breadcrumb** bar with a toggle to an
  **editable address entry**.
- Sidebar: **Places**, **Bookmarks**, **Devices** (a disk→volumes tree), and a
  **Network** placeholder. Bookmarks persist to `~/.config/ribbonfm/`.
- Unmounted disks can be **mounted on click**; real mount points are listed even
  where `Gio.VolumeMonitor` reports none.

### Views
- Icon modes: extra large / large / medium / small / tiles (real icon resizing),
  plus list, details, content and thumbnail.
- Sort by name/size/type/mtime; directories always first; group by type.
- In-folder search/filter; show hidden files; **view toggles** for item
  checkboxes and file extensions.
- Multi-select (rubber-band, Ctrl/Shift) with **Select All / None / Invert**;
  optional **checkbox column**.
- **Drag & drop**: drag files/folders (also cross-application via
  `text/uri-list`) onto folder rows or the background; Ctrl-drag moves.

### File operations (async I/O)
- New folder / file, cut / copy / paste, rename, **move to Trash**
  (`Gio.File.trash`), permanent delete, properties.
- Open with default app, or **Open With…** — lists all installed apps, searchable,
  with **custom program path** selection.
- Right-click context menus for items and the folder background.
- **Open Terminal** launches the system default terminal in the current folder.

### Properties page (Windows-style)
- Tabbed dialog: **General / Security / Details** with object name, a permission
  matrix (owner/group/other × r/w/x), octal-mode editor, size and timestamps.
- Opens as a **non-modal** window so you can keep working.

### Permissions & privilege escalation
- Displays `rwx`, octal mode, owner/group in views and properties.
- **Never runs elevated.** Privileged ops (`chmod`/`chown`) escalate per action:
  `pkexec` (Linux), UAC `runas` (Windows), Authorization Services (macOS).
- `777` is not refused (just warned); read-only mounts are detected.
- See [`doc/SECURITY.md`](doc/SECURITY.md).

### i18n
- All strings through gettext `_()`; ships `en` + `zh_CN`, extensible.
- Automatic locale detection + runtime language switch (restart to refresh).

---

## Getting started

```sh
# Linux: install GTK3 + PyGObject (system package), then:
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e . pytest
python tools/gen_po.py          # build translation catalogs
ribbonfm                        # or: python -m ribbonfm
```

`--system-site-packages` lets the venv see the distribution's GTK bindings
(`gi`). For an isolated venv, install PyGObject for your interpreter first
(e.g. `apt install python3-gi`).

---

## Testing

```sh
python -m unittest discover -s tests -v
```

Core tests only need `gi` (Gio/GLib) and no display; CI runs them on the system
python3 after `apt install python3-gi`.

---

## Building releases

| Platform | Output | How |
| --- | --- | --- |
| Linux `.deb` (self-contained) | `build/deb/RibbonFM_*.deb` | `bash pack/linux/build_deb.sh` |
| Linux `AppImage` | `dist/RibbonFileManager-*.AppImage` | `bash pack/appimage/build.sh` |
| Windows portable ZIP | `dist/RibbonFM-*-windows-x86_64.zip` | `python pack/windows/build_portable.py` (MSYS2) |

CI/CD (`.github/workflows/`):
- `ci.yml` — lint (flake8), tests, Glade/compile validation.
- `release.yml` — on `v*` tags builds the `.deb`, `AppImage` and Windows ZIP and
  attaches them to a GitHub Release.

---

## Project layout

```
src/ribbonfm/     application (core/ logic separated from ui/ widgets)
  core/           pathutils, files, perm, mounts, sorts, tasks (async)
  ui/             mainwindow, navigation, ops, ribbon, fileview, propsdialog...
  resources/      *.glade (GtkBuilder), css, locale/<lang>/*.mo
data/             desktop file, icon, AppStream metadata
pack/             flatpak, appimage, linux(deb/pyinstaller), windows, macos
doc/              install, architecture, security docs
po/               gettext catalogs + generator (tools/gen_po.py)
tests/            unit tests (no display required)
INDEX.md          auditable code index (regenerate: python tools/gen_index.py)
```

## Translations

Add a language to `TRANSLATIONS` in `tools/gen_po.py`, then:

```sh
python tools/gen_po.py
```

---

## License

[Apache License 2.0](LICENSE). GTK3 / PyGObject are LGPL; this project contains
**no GPL code**.
