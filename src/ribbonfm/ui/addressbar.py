"""Breadcrumb navigation bar and editable address entry.

The widget renders one :class:`Gtk.Button` per path segment (with ``/`` icons
between them) inside ``crumb_bar``. The companion ``address_entry`` is shown when
the user wants to type a path directly; the two views are swapped by a toggle.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from gi.repository import Gtk, Pango

from .. import i18n


class AddressBar:
    def __init__(self, crumb_bar: Gtk.Box, entry: Gtk.Entry,
                 toggle_btn: Gtk.Button, on_navigate: Callable[[str], None]):
        self._crumb_bar = crumb_bar
        self._entry = entry
        self._toggle_btn = toggle_btn
        self._on_navigate = on_navigate
        self._path = "/"
        self._in_edit = False
        # Breadcrumbs are the default view; the editable entry is hidden until
        # the user explicitly toggles into edit mode.
        self._crumb_bar.set_visible(True)
        self._entry.set_visible(False)
        self._toggle_btn.connect("clicked", self._on_toggle)
        self._entry.connect("activate", self._on_entry_activate)

    def _on_toggle(self, _btn=None):
        self._set_edit_mode(not self._in_edit)

    def _set_edit_mode(self, edit: bool) -> None:
        self._in_edit = edit
        if edit:
            self._crumb_bar.set_visible(False)
            self._entry.set_visible(True)
            self._entry.set_text(self._path)
            self._entry.grab_focus()
        else:
            self._entry.set_visible(False)
            self._crumb_bar.set_visible(True)
            self._rebuild_crumbs()

    def _on_entry_activate(self, entry: Gtk.Entry, *_):
        value = entry.get_text().strip()
        self._set_edit_mode(False)
        if value:
            self._on_navigate(value)

    def set_path(self, path: str, *, rebuild: bool = True) -> None:
        self._path = path
        if self._in_edit:
            self._entry.set_text(path)
        if rebuild:
            self._rebuild_crumbs()

    def _rebuild_crumbs(self) -> None:
        for child in self._crumb_bar.get_children():
            self._crumb_bar.remove(child)
        path = Path(self._path)
        if path.is_absolute():
            self._add_crumb("/", "/")
            current = "/"
            for part in path.parts[1:]:
                self._add_separator()
                current = str(Path(current) / part)
                self._add_crumb(part, current)
        else:
            self._add_crumb(str(path), str(path))
        self._crumb_bar.show_all()  # crumbs are (re)built, so reveal them

    def _add_separator(self) -> None:
        sep = Gtk.Image.new_from_icon_name("go-next-symbolic", Gtk.IconSize.MENU)
        sep.set_size_request(18, 18)
        self._crumb_bar.pack_start(sep, False, False, 0)

    def _add_crumb(self, label: str, path: str) -> None:
        btn = Gtk.Button()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_label(label)
        btn.set_tooltip_text(path)
        btn._crumb_path = path
        btn.connect("clicked", self._on_crumb_click)
        self._crumb_bar.pack_start(btn, False, False, 0)

    def _on_crumb_click(self, btn: Gtk.Button) -> None:
        self._on_navigate(btn._crumb_path)

    def show_entry(self) -> None:
        self._set_edit_mode(True)
