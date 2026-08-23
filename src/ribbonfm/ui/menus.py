"""Context menu builders for the file view.

Two menus are produced:

* **item menu** -- shown when right-clicking on a selected file/directory.
* **background menu** -- shown when right-clicking on empty space in the folder.

Items emit callback actions that the main window wires to the controller; the
buttons carry an ``_action`` attribute exactly like the Ribbon buttons so the
controller dispatches them through the same :meth:`handle_action` entry point.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from gi.repository import Gtk

from .. import i18n


def build_item_menu(path: str, selected: List[str],
                    dispatch: Callable[[str], None]) -> Gtk.Menu:
    menu = Gtk.Menu()

    def _act(action, label, icon=None, sensitive=True):
        if icon:
            item = Gtk.ImageMenuItem.new_with_label(label)
            item.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU))
        else:
            item = Gtk.MenuItem(label=label)
        item.set_sensitive(sensitive)
        item._action = action
        item.connect("activate", lambda w: dispatch(w._action))
        menu.append(item)

    _act("open", i18n._("Open"), "document-open")
    _act("open_with", i18n._("Open With..."), "applications-other")
    menu.append(Gtk.SeparatorMenuItem())
    _act("cut", i18n._("Cut"), "edit-cut")
    _act("copy", i18n._("Copy"), "edit-copy")
    _act("rename", i18n._("Rename..."), "edit-rename")
    menu.append(Gtk.SeparatorMenuItem())
    _act("delete", i18n._("Move to Trash"), "user-trash", sensitive=True)
    _act("delete_permanent", i18n._("Delete Permanently"), "edit-delete")
    menu.append(Gtk.SeparatorMenuItem())
    _act("properties", i18n._("Properties"), "document-properties")
    return menu


def build_background_menu(current_path: str,
                          dispatch: Callable[[str], None]) -> Gtk.Menu:
    menu = Gtk.Menu()

    def _act(action, label, icon=None):
        if icon:
            item = Gtk.ImageMenuItem.new_with_label(label)
            item.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU))
        else:
            item = Gtk.MenuItem(label=label)
        item._action = action
        item.connect("activate", lambda w: dispatch(w._action))
        menu.append(item)

    _act("new_folder", i18n._("New Folder"), "folder-new")
    _act("new_file", i18n._("New File"), "text-x-generic")
    menu.append(Gtk.SeparatorMenuItem())
    _act("paste", i18n._("Paste"), "edit-paste")
    _act("select_all", i18n._("Select All"), "edit-select-all")
    menu.append(Gtk.SeparatorMenuItem())
    _act("refresh", i18n._("Refresh"), "view-refresh")
    _act("properties", i18n._("Properties"), "document-properties")
    return menu


def popup(menu: Gtk.Menu, event) -> None:
    menu.show_all()
    menu.popup(None, None, None, None, event.button, event.time)
