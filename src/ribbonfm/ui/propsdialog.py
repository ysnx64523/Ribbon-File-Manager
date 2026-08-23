"""Windows-style properties page.

A tabbed properties dialog emulating the Windows Explorer layout:

* **General** (常规): icon + name, file type, location, size, created /
  modified / accessed times, and read-only / hidden attributes.
* **Security** (安全): object name, a permission matrix for owner / group /
  other with read / write / execute columns, and a functional octal-mode editor.
* **Details** (详细信息): a detailed key/value list.

Permission changes go through :mod:`ribbonfm.core.perm` which escalates via
``pkexec`` when the user lacks rights.
"""

from __future__ import annotations

import datetime
import os

from gi.repository import Gtk

from .. import i18n
from ..core import files, perm
from . import dialogs


class PropertiesDialog:
    def __init__(self, parent, path: str):
        self._parent = parent
        self._path = path
        self._entry = files.entry_for_path(path)
        if self._entry.is_symlink:
            self._kind = "link"
        else:
            self._kind = "folder" if self._entry.is_dir else "file"
        self._hint = perm.inspect(path)
        self._st = os.stat(path)

    def run(self) -> None:
        dialog = Gtk.Dialog(transient_for=self._parent, modal=False,
                            title=i18n._("Properties"))
        dialog.set_default_size(500, 420)
        dialog.add_buttons(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        area = dialog.get_content_area()
        area.set_margin_start(6)
        area.set_margin_end(6)
        area.set_margin_top(6)
        area.set_margin_bottom(6)

        notebook = Gtk.Notebook()
        notebook.append_page(self._build_general_tab(), Gtk.Label(label=i18n._("General")))
        notebook.append_page(self._build_security_tab(), Gtk.Label(label=i18n._("Security")))
        notebook.append_page(self._build_details_tab(), Gtk.Label(label=i18n._("Details")))
        area.pack_start(notebook, True, True, 0)

        if self._hint.warning:
            note = Gtk.Label(label=i18n._(
                "This location is writable by all users or is managed with "
                "elevated privileges."))
            note.set_line_wrap(True)
            note.set_xalign(0)
            note.get_style_context().add_class("security-note")
            area.pack_start(note, False, False, 8)

        dialog.show_all()
        # Non-modal: keep the file manager usable; close on any response.
        dialog.connect("response", lambda d, _r: d.destroy())
        self._dialog = dialog

    # --- General ------------------------------------------------------------

    def _build_general_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        image = Gtk.Image.new_from_icon_name(
            "folder" if self._entry.is_dir else "text-x-generic", Gtk.IconSize.DIALOG)
        name = Gtk.Label(label=self._entry.display_name)
        name.set_xalign(0.5)
        name.set_line_wrap(True)
        name.get_style_context().add_class("prop-title")
        header.pack_start(image, False, False, 0)
        header.pack_start(name, True, True, 0)
        box.pack_start(header, False, False, 0)

        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(8)
        rows = [
            (i18n._("File type"), self._type_label()),
            (i18n._("Location"), self._entry.path),
            (i18n._("Size"), self._size_label()),
            (i18n._("Size on disk"), self._size_label()),
            (i18n._("Created"), self._time(self._st.st_ctime)),
            (i18n._("Modified"), self._time(self._st.st_mtime)),
            (i18n._("Accessed"), self._time(self._st.st_atime)),
        ]
        for i, (k, v) in enumerate(rows):
            self._add_grid_row(grid, i, k, v)
        box.pack_start(grid, True, True, 0)

        attrs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        readonly = bool(self._hint.rwx and not self._hint.rwx[1] == "w")
        hidden = self._entry.name.startswith(".")
        for label, active in ((i18n._("Read-only"), readonly),
                              (i18n._("Hidden"), hidden)):
            chk = Gtk.CheckButton(label=label)
            chk.set_active(active)
            attrs.pack_start(chk, False, False, 0)
        box.pack_start(attrs, False, False, 4)
        return box

    # --- Security ------------------------------------------------------------

    def _build_security_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        self._add_plain_row(box, i18n._("Object name"), self._entry.path)
        self._add_plain_row(box, i18n._("Owner"), self._hint.user_name)
        self._add_plain_row(box, i18n._("Group"), self._hint.group_name)

        if not self._hint.rwx:
            box.pack_start(Gtk.Label(label=i18n._("Permissions are not available.")),
                           False, False, 4)
            return box
        frame = Gtk.Frame(label=i18n._("Permissions"))
        self._add_perm_matrix(frame)
        box.pack_start(frame, True, True, 4)

        editor = self._build_perm_editor()
        if editor is not None:
            box.pack_start(editor, False, False, 4)
        return box

    def _add_perm_matrix(self, frame) -> None:
        mode = self._hint.rwx
        grid = Gtk.Grid()
        grid.set_column_spacing(14)
        grid.set_row_spacing(4)
        grid.set_margin_start(8)
        grid.set_margin_end(8)
        grid.set_margin_top(8)
        grid.set_margin_bottom(8)
        headers = ["", i18n._("Read"), i18n._("Write"), i18n._("Execute")]
        for c, h in enumerate(headers):
            lbl = Gtk.Label(label=h)
            lbl.get_style_context().add_class("prop-key")
            grid.attach(lbl, c, 0, 1, 1)
        rows = [
            (i18n._("Owner"), mode[0:3]),
            (i18n._("Group"), mode[3:6]),
            (i18n._("Others"), mode[6:9]),
        ]
        for r, (name, bits) in enumerate(rows, start=1):
            lbl = Gtk.Label(label=name)
            lbl.set_xalign(0)
            grid.attach(lbl, 0, r, 1, 1)
            for c in range(3):
                chk = Gtk.CheckButton()
                chk.set_active(bits[c] != "-")
                chk.set_sensitive(False)
                grid.attach(chk, c + 1, r, 1, 1)
        frame.add(grid)
        frame.show_all()

    def _build_perm_editor(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(8)
        lbl = Gtk.Label(label=i18n._("Octal mode"))
        lbl.get_style_context().add_class("prop-key")
        box.pack_start(lbl, False, False, 0)
        entry = Gtk.Entry()
        entry.set_text(self._hint.octal or "755")
        entry.set_width_chars(6)
        entry.set_tooltip_text(i18n._("Octal mode, e.g. 755"))
        box.pack_start(entry, False, False, 0)

        def apply(_btn):
            text = entry.get_text().strip()
            try:
                mode = int(text, 8)
            except ValueError:
                dialogs.show_error(self._parent, i18n._("Invalid octal mode"),
                                   i18n._("Use a value such as 755."))
                return
            ok, msg = perm.chmod(self._path, mode)
            if not ok:
                dialogs.show_error(self._parent, msg)
            else:
                dialogs.show_info(self._parent, i18n._("Permissions updated."))

        btn = Gtk.Button(label=i18n._("Edit"))
        btn.connect("clicked", apply)
        box.pack_start(btn, False, False, 0)
        return box

    # --- Details -------------------------------------------------------------

    def _build_details_tab(self) -> Gtk.Widget:
        grid = Gtk.Grid()
        grid.set_column_spacing(16)
        grid.set_row_spacing(6)
        grid.set_margin_start(12)
        grid.set_margin_end(12)
        grid.set_margin_top(12)
        grid.set_margin_bottom(12)
        rows = [
            (i18n._("Name"), self._entry.display_name),
            (i18n._("Type"), self._kind),
            (i18n._("Size"), self._size_label()),
            (i18n._("Created"), self._time(self._st.st_ctime)),
            (i18n._("Modified"), self._time(self._st.st_mtime)),
            (i18n._("Accessed"), self._time(self._st.st_atime)),
            (i18n._("Permissions"), self._hint.rwx),
            (i18n._("Octal mode"), self._hint.octal),
            (i18n._("Owner"), self._hint.user_name),
            (i18n._("Group"), self._hint.group_name),
            (i18n._("Path"), self._entry.path),
        ]
        for i, (k, v) in enumerate(rows):
            self._add_grid_row(grid, i, k, v)
        scroller = Gtk.ScrolledWindow()
        scroller.add(grid)
        return scroller

    # --- helpers --------------------------------------------------------------

    def _add_grid_row(self, grid, row, label, value) -> None:
        k = Gtk.Label(label=label)
        k.set_xalign(0)
        k.get_style_context().add_class("prop-key")
        v = Gtk.Label(label=value)
        v.set_xalign(0)
        v.set_hexpand(True)
        v.set_selectable(True)
        v.set_ellipsize(3)
        grid.attach(k, 0, row, 1, 1)
        grid.attach(v, 1, row, 1, 1)

    def _add_plain_row(self, box, label, value) -> None:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        k = Gtk.Label(label=label)
        k.set_xalign(0)
        k.get_style_context().add_class("prop-key")
        v = Gtk.Label(label=value)
        v.set_xalign(0)
        v.set_ellipsize(3)
        v.set_selectable(True)
        row.pack_start(k, False, False, 0)
        row.pack_start(v, True, True, 0)
        box.pack_start(row, False, False, 0)

    def _type_label(self) -> str:
        if self._entry.is_symlink:
            return i18n._("Symbolic link to {t}").format(
                t=self._entry.symlink_target or "")
        return {
            "folder": i18n._("Folder"),
            "drive": i18n._("Drive"),
            "link": i18n._("Symbolic link"),
            "file": i18n._("File"),
        }.get(self._kind, self._kind)

    def _size_label(self) -> str:
        if self._entry.is_dir:
            return i18n._("(folder)")
        return _size_human(self._entry.size)

    @staticmethod
    def _time(epoch: float) -> str:
        if not epoch:
            return ""
        return datetime.datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")


def _size_human(size: int) -> str:
    s = float(size)
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while s >= 1024 and i < len(units) - 1:
        s /= 1024
        i += 1
    return f"{int(s)} {units[i]}" if i == 0 else f"{s:.1f} {units[i]}"
