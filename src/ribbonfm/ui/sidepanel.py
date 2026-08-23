"""Collapsible navigation sidebar.

Sections are rendered as expandable tree rows: **Places**, **Bookmarks**,
**Devices** and a **Network** placeholder. Each entry holds a GIO-backed path;
clicking navigates there. Bookmarks are persisted to a small JSON file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from gi.repository import Gtk, Gdk, Gio, Pango

from .. import config
from .. import i18n
from ..core import mounts, pathutils

_ICON_COL = 0
_NAME_COL = 1
_PATH_COL = 2
_KIND_COL = 3

_SECTION = "section"
_ITEM = "item"


class Sidebar:
    def __init__(self, container: Gtk.Box, on_navigate: Callable[[str], None]):
        self._on_navigate = on_navigate
        self._bookmarks: list[tuple[str, str] | list[str]] = []
        self._notebook_path = config.SETTINGS_DIR / "bookmarks.json"
        self._mount_map: dict[str, object] = {}
        self._load_bookmarks()

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.show()

        self._model = Gtk.TreeStore(str, str, str, str)
        self._view = Gtk.TreeView(model=self._model)
        self._view.set_headers_visible(False)
        self._view.set_level_indentation(14)
        self._view.set_enable_tree_lines(True)
        self._view.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        self._view.connect("row-activated", self._on_activated)
        self._view.connect("button-press-event", self._on_button_press)

        cell_icon = Gtk.CellRendererPixbuf()
        cell_text = Gtk.CellRendererText()
        text_col = Gtk.TreeViewColumn(None)
        text_col.pack_start(cell_icon, False)
        text_col.pack_start(cell_text, True)
        text_col.add_attribute(cell_icon, "icon-name", _ICON_COL)
        text_col.add_attribute(cell_text, "text", _NAME_COL)
        self._view.append_column(text_col)

        scroller.add(self._view)
        container.pack_start(scroller, True, True, 0)
        container.show_all()

        self.refresh()

    # --- persistence ------------------------------------------------------

    def _load_bookmarks(self) -> None:
        try:
            raw = json.loads(self._notebook_path.read_text("utf-8"))
            self._bookmarks = raw
        except (OSError, ValueError):
            self._bookmarks = []

    def _save_bookmarks(self) -> None:
        try:
            config.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
            self._notebook_path.write_text(
                json.dumps(self._bookmarks, ensure_ascii=False, indent=2), "utf-8")
        except OSError:
            pass

    # --- rendering ---------------------------------------------------------

    def refresh(self) -> None:
        self._model.clear()
        self._build_section(i18n._("Places"), "user-home", self._places())
        self._build_section(i18n._("Bookmarks"), "user-bookmarks",
                            [(name, path, "user-bookmarks") for name, path
                             in [(b[0], b[1]) for b in self._bookmarks]])
        self._build_devices()
        self._build_section(i18n._("Network"), "network-wired",
                            [(i18n._("Network locations"), "", "network-wired")])

    def _build_devices(self) -> None:
        """List disks as an expandable tree: drive -> volumes."""

        def icon_of(gicon) -> str:
            try:
                names = list(gicon.get_names()) if hasattr(gicon, "get_names") else []
                return names[0] if names else "drive-harddisk"
            except Exception:
                return "drive-harddisk"

        self._mount_map.clear()
        parent = self._model.append(None, ["drive-harddisk", i18n._("Devices"),
                                           "", _SECTION])
        # Group volumes under their physical drive (Gio.Drive); volumes without
        # a drive go straight under Devices.
        drive_nodes: dict[str, object] = {}
        for m in mounts.list_mounts():
            drive = m.volume.get_drive() if m.volume is not None else None
            if drive is not None:
                dname = drive.get_name() or i18n._("Drive")
                node = drive_nodes.get(dname)
                if node is None:
                    node = self._model.append(
                        parent, [icon_of(drive.get_icon()), dname, "", _SECTION])
                    drive_nodes[dname] = node
            else:
                node = parent
            token = m.uri or (m.path or "")
            if not token:
                continue
            self._mount_map[token] = m
            label = m.name
            if not m.mounted:
                label = f"{label} ({i18n._('Not mounted')})"
            self._model.append(node, [m.icon_name or "drive-harddisk", label,
                                      token, _ITEM])
        self._view.expand_row(self._model.get_path(parent), False)
        for node in drive_nodes.values():
            self._view.expand_row(self._model.get_path(node), False)

    def _places(self) -> list[tuple[str, str, str]]:
        places: list[tuple[str, str, str]] = []
        for _key, path, icon in pathutils.special_navigation():
            places.append((_human_label(_key), str(path), icon))
        for extra in ("/", str(pathutils.HOME_DIR)):
            if str(pathutils.HOME_DIR) != extra:
                places.append((i18n._("File system"), "/", "drive-harddisk"))
        return places

    def _build_section(self, label: str, icon: str,
                       items: list[tuple[str, str, str]]) -> None:
        parent = self._model.append(None, [icon, label, "", _SECTION])
        for name, path, ic in items:
            if not path:
                continue
            self._model.append(parent, [ic or "document", name, path, _ITEM])
        self._view.expand_row(self._model.get_path(parent), False)

    # --- events ------------------------------------------------------------

    def _on_activated(self, _view, treepath, _col):
        model = self._model
        it = model.get_iter(treepath)
        if model.get_value(it, _KIND_COL) == _ITEM:
            self._activate_token(model.get_value(it, _PATH_COL))

    def _activate_token(self, token: str) -> None:
        info = self._mount_map.get(token)
        if info is not None:
            if info.mounted and info.path:
                self._on_navigate(info.path)
            else:
                mounts.mount_volume(info, self._on_mount_done)
            return
        if token:
            self._on_navigate(token)

    def _on_mount_done(self, path: str, error: str) -> None:
        from . import dialogs
        if error:
            dialogs.show_error(None, i18n._("Could not mount device"), error)
            return
        self.refresh()
        if path:
            self._on_navigate(path)

    def _on_button_press(self, view, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            path, col, x, y = view.get_path_at_pos(int(event.x), int(event.y))
            if path:
                it = self._model.get_iter(path)
                if self._model.get_value(it, _KIND_COL) == _ITEM:
                    self._activate_token(self._model.get_value(it, _PATH_COL))
                    return True
        elif event.button == Gdk.BUTTON_SECONDARY:
            if self._show_context_menu(view, event):
                return True
        return False

    def _show_context_menu(self, view, event) -> bool:
        path, _, _, _ = view.get_path_at_pos(int(event.x), int(event.y))
        if not path:
            return False
        it = self._model.get_iter(path)
        if self._model.get_value(it, _KIND_COL) != _ITEM:
            return False
        name = self._model.get_value(it, _NAME_COL)
        full = self._model.get_value(it, _PATH_COL)
        menu = Gtk.Menu()

        def _insert(label, icon, cb):
            item = Gtk.ImageMenuItem.new_with_label(label)
            item.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU))
            item.connect("activate", cb)
            menu.append(item)

        _insert(i18n._("Open"), "document-open", lambda *_: self._on_navigate(full))
        _insert(i18n._("Add to bookmarks"), "bookmark-new",
                lambda *_: self.add_bookmark(name, full))
        _insert(i18n._("Remove bookmark"), "user-trash",
                lambda *_: self.remove_bookmark(name, full))
        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)
        return True

    # --- bookmarks API -----------------------------------------------------

    def add_bookmark(self, name: str, path: str) -> None:
        for b in list(self._bookmarks):
            if b[1] == path:
                return
        self._bookmarks.append([name, path])
        self._save_bookmarks()
        self.refresh()

    def remove_bookmark(self, name: str, path: str) -> None:
        self._bookmarks = [b for b in self._bookmarks if b[1] != path]
        self._save_bookmarks()
        self.refresh()


def _human_label(key: str) -> str:
    mapping = {
        "home": ("Home"),
        "desktop": ("Desktop"),
        "documents": ("Documents"),
        "downloads": ("Downloads"),
        "pictures": ("Pictures"),
        "music": ("Music"),
        "videos": ("Videos"),
    }
    label = mapping.get(key, key)
    # Wrap with gettext so translators get a PO entry.
    return i18n._(label)
