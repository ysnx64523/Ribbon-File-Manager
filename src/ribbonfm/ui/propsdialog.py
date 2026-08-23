"""Properties dialog.

Shows metadata for a single file or directory. On Unix it also shows the POSIX
mode as ``rwx`` and lets the user change permissions and ownership. Changing
permissions uses :mod:`ribbonfm.core.perm` which escalates through ``pkexec``
when the current user lacks rights -- the dialog never runs elevated itself.
"""

from __future__ import annotations

import datetime
from typing import Optional

from gi.repository import Gtk, GLib

from .. import i18n
from ..core import files, perm, pathutils
from . import dialogs


class PropertiesDialog:
    def __init__(self, parent, path: str):
        self._parent = parent
        self._path = path
        self._entry = files.entry_for_path(path)
        self._kind = pathutils.kind_label(self._entry)

    def run(self) -> None:
        dialog = Gtk.Dialog(transient_for=self._parent, modal=True,
                            title=i18n._("Properties"))
        dialog.set_default_size(420, -1)
        dialog.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        area = dialog.get_content_area()
        area.set_spacing(0)
        area.set_margin_top(10)
        area.set_margin_bottom(10)
        area.set_margin_start(12)
        area.set_margin_end(12)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(8)
        area.pack_start(grid, True, True, 0)

        row = 0
        self._add_grid_row(grid, row, i18n._("Name"), self._entry.display_name); row += 1
        self._add_grid_row(grid, row, i18n._("Type"), self._type_label()); row += 1
        self._add_grid_row(grid, row, i18n._("Location"), self._entry.path); row += 1
        self._add_grid_row(grid, row, i18n._("Size"), self._size_label()); row += 1
        self._add_grid_row(grid, row, i18n._("Modified"),
                           self._time(self._entry.mtime)); row += 1

        warning = perm.inspect(self._path)
        if warning.rwx:
            self._add_grid_row(grid, row, i18n._("Permissions"), warning.rwx); row += 1
            self._add_grid_row(grid, row, i18n._("Owner"), warning.user_name); row += 1
            self._add_grid_row(grid, row, i18n._("Group"), warning.group_name); row += 1
            self._add_grid_row(grid, row, i18n._("Octal mode"), warning.octal); row += 1

        if warning.warning:
            note = Gtk.Label(label=i18n._(
                "This location is writable by all users or is managed with "
                "elevated privileges."))
            note.set_wrap(True)
            note.set_xalign(0)
            note.get_style_context().add_class("security-note")
            area.pack_start(note, False, False, 8)

        if warning.rwx:
            self._build_perm_editor(area, dialog, warning)

        dialog.show_all()
        dialog.run()
        dialog.destroy()

    # --- helpers -----------------------------------------------------------

    def _add_grid_row(self, grid, row, label, value) -> None:
        lbl = Gtk.Label(label=label)
        lbl.set_xalign(0)
        lbl.get_style_context().add_class("prop-key")
        val = Gtk.Label(label=value)
        val.set_xalign(0)
        val.set_hexpand(True)
        val.set_selectable(True)
        val.set_ellipsize(3)  # Pango.EllipsizeMode.END
        grid.attach(lbl, 0, row, 1, 1)
        grid.attach(val, 1, row, 1, 1)
        grid.show_all()

    def _build_perm_editor(self, area, dialog, hint) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(10)
        head = Gtk.Label(label=i18n._("Change permissions"))
        head.set_xalign(0)
        head.get_style_context().add_class("prop-key")
        box.pack_start(head, False, False, 0)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mode_entry = Gtk.Entry()
        mode_entry.set_text(hint.octal or "755")
        mode_entry.set_width_chars(6)
        mode_entry.set_tooltip_text(i18n._("Octal mode, e.g. 755"))
        row.pack_start(mode_entry, False, False, 0)

        def on_apply(_btn):
            text = mode_entry.get_text().strip()
            try:
                mode = int(text, 8)
            except ValueError:
                dialogs.show_error(dialog, i18n._("Invalid octal mode"),
                                   i18n._("Use a value such as 755."))
                return
            ok, msg = perm.chmod(self._path, mode)
            if not ok:
                dialogs.show_error(dialog, msg)
            else:
                dialogs.show_info(dialog, i18n._("Permissions updated."))

        apply_btn = Gtk.Button(label=i18n._("Apply"))
        apply_btn.connect("clicked", on_apply)
        row.pack_start(apply_btn, False, False, 0)
        box.pack_start(row, False, False, 0)
        area.pack_start(box, False, False, 0)

    def _type_label(self) -> str:
        kind = self._kind
        if self._entry.is_symlink:
            target = self._entry.symlink_target or ""
            return i18n._("Symbolic link to {target}").format(target=target)
        labels = {
            "folder": i18n._("Folder"),
            "drive": i18n._("Drive"),
            "link": i18n._("Symbolic link"),
            "file": i18n._("File"),
        }
        return labels.get(kind, kind)

    def _size_label(self) -> str:
        if self._entry.is_dir:
            return i18n._("(folder)") + " " + str(self._entry.size) + " B"
        return _size_human(self._entry.size)

    @staticmethod
    def _time(epoch: int) -> str:
        if not epoch:
            return ""
        return datetime.datetime.fromtimestamp(epoch).strftime(
            "%Y-%m-%d %H:%M:%S")


def _size_human(size: int) -> str:
    s = float(size)
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while s >= 1024 and i < len(units) - 1:
        s /= 1024
        i += 1
    return f"{int(s)} {units[i]}" if i == 0 else f"{s:.1f} {units[i]}"
