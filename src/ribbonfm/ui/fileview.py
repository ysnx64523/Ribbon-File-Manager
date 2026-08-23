"""The main file browsing view.

Wraps a :class:`Gtk.TreeView` (list/details modes) and a :class:`Gtk.IconView`
(icon modes) that share a single :class:`Gtk.ListStore`. Sorting always keeps
directories first, and a lightweight name filter supports fast in-folder search.
Icons are resolved from the content type through the icon theme.
"""

from __future__ import annotations

import os
from typing import Callable, Optional

from gi.repository import Gtk, Gdk, Gio, GdkPixbuf, GLib, Pango

from .. import i18n
from ..core import files

# ListStore columns
COL_PATH = 0
COL_NAME = 1
COL_ICON = 2
COL_IS_DIR = 3
COL_SIZE = 4
COL_TYPE = 5
COL_MTIME = 6
COL_MODE = 7
COL_OWNER = 8
COL_GROUP = 9
COL_ICON_PIXBUF = 10
COL_CHECKED = 11

_VIEW_KEYS = ("huge", "large", "medium", "small", "list", "details", "tiles", "content", "thumb")

# icon-view modes -> item width (px)
_ICON_WIDTHS = {"huge": 190, "large": 150, "medium": 130, "small": 100,
                "tiles": 165, "thumb": 190}

_icon_cache: dict[str, str] = {}
_pixbuf_cache: dict[str, GdkPixbuf.Pixbuf] = {}
_ICON_PIX = 48


def _icon_for(entry: files.FileEntry) -> str:
    key = entry.content_type or entry.name
    if key in _icon_cache:
        return _icon_cache[key]
    icon = "text-x-generic"
    if entry.is_dir:
        icon = "folder"
    elif entry.is_symlink:
        icon = "emblem-symbolic-link"
    else:
        try:
            gicon = Gio.content_type_get_icon(entry.content_type)
            names = list(gicon.get_names())
            if names:
                icon = names[0]
        except Exception:
            icon = "text-x-generic"
    _icon_cache[key] = icon
    return icon


def _size_str(size: int) -> str:
    if size == 0:
        return ""
    return format_size(size)


def _icon_pixbuf(icon_name: str) -> Optional[GdkPixbuf.Pixbuf]:
    icon_name = icon_name or "text-x-generic"
    if icon_name in _pixbuf_cache:
        return _pixbuf_cache[icon_name]
    try:
        theme = Gtk.IconTheme.get_default()
        if theme.has_icon(icon_name):
            pix = theme.load_icon(icon_name, _ICON_PIX,
                                  Gtk.IconLookupFlags.FORCE_SIZE)
        else:
            pix = theme.load_icon("text-x-generic", _ICON_PIX,
                                  Gtk.IconLookupFlags.FORCE_SIZE)
    except (GLib.Error, Exception):
        pix = None
    if pix is not None:
        _pixbuf_cache[icon_name] = pix
    return pix


def format_size(size: int | float) -> str:
    size = float(size)
    units = ["B", "KB", "MB", "GB", "TB"]
    u = 0
    while size >= 1024 and u < len(units) - 1:
        size /= 1024
        u += 1
    return f"{int(size)} {units[u]}" if u == 0 else f"{size:.1f} {units[u]}"


class FileView:
    def __init__(self, tree_view: Gtk.TreeView, icon_view: Gtk.IconView,
                 view_stack: Gtk.Stack,
                 on_activate: Callable[[str], None],
                 on_context_menu: Callable[[str, bool], None],
                 on_visible_change: Optional[Callable] = None):
        self._tree = tree_view
        self._icons = icon_view
        self._stack = view_stack
        self._on_activate = on_activate
        self._on_context_menu = on_context_menu
        self._on_visible_change = on_visible_change
        self._mode = "details"
        self._show_hidden = False
        self._filter_text = ""
        self._suppress_sync = False

        self._base = Gtk.ListStore(
            str,          # COL_PATH
            str,          # COL_NAME
            str,          # COL_ICON
            bool,         # COL_IS_DIR
            int,          # COL_SIZE (raw bytes; formatted on render)
            str,          # COL_TYPE
            int,          # COL_MTIME (epoch; formatted on render)
            str,          # COL_MODE
            str,          # COL_OWNER
            str,          # COL_GROUP
            GdkPixbuf.Pixbuf,  # COL_ICON_PIXBUF
            bool,         # COL_CHECKED (selection checkbox)
        )
        self._sort = Gtk.TreeModelSort(model=self._base)
        self._sort.set_sort_func(COL_NAME, self._dirs_first, None)
        self._sort.set_sort_column_id(COL_NAME, Gtk.SortType.ASCENDING)
        self._filter = Gtk.TreeModelFilter(child_model=self._sort)
        self._filter.set_visible_func(self._filter_visible, None)

        self._setup_tree()
        self._setup_iconview()

        self._tree.set_model(self._filter)
        self._icons.set_model(self._filter)

        self._tree.connect("row-activated", self._row_activated)
        self._icons.connect("item-activated", self._row_activated)
        self._tree.connect("button-press-event", self._button_press)
        self._icons.connect("button-press-event", self._button_press)

        # Multi-select support: ctrl-click, shift-click and rubber-band (框选).
        self._tree.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self._tree.get_selection().connect("changed", self._on_selection_changed)

        self._set_view(self._mode)

    # --- column setup -------------------------------------------------------

    def _pixbuf_col(self, title: str, width: int) -> Gtk.TreeViewColumn:
        col = Gtk.TreeViewColumn(title)
        cell = Gtk.CellRendererPixbuf()
        text = Gtk.CellRendererText()
        col.pack_start(cell, False)
        col.pack_start(text, True)
        col.add_attribute(cell, "icon-name", COL_ICON)
        col.add_attribute(text, "text", COL_NAME)
        col.set_sort_column_id(COL_NAME)
        return col

    def _setup_tree(self) -> None:
        tree = self._tree
        for col in list(tree.get_columns()):
            tree.remove_column(col)

        # Selection checkbox column (Checkboxes view: check state == selection).
        check_cell = Gtk.CellRendererToggle()
        check_col = Gtk.TreeViewColumn(None)
        check_col.pack_start(check_cell, False)
        check_col.add_attribute(check_cell, "active", COL_CHECKED)
        check_cell.connect("toggled", self._on_check_toggled)
        check_col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        check_col.set_fixed_width(30)
        tree.append_column(check_col)

        name_col = Gtk.TreeViewColumn(i18n._("Name"))
        cell_icon = Gtk.CellRendererPixbuf()
        cell_name = Gtk.CellRendererText()
        cell_name.set_property("ellipsize", Pango.EllipsizeMode.END)
        name_col.pack_start(cell_icon, False)
        name_col.pack_start(cell_name, True)
        name_col.add_attribute(cell_icon, "icon-name", COL_ICON)
        name_col.add_attribute(cell_name, "text", COL_NAME)
        name_col.set_sort_column_id(COL_NAME)
        name_col.set_expand(True)
        tree.append_column(name_col)

        def _add_text_col(title, attr, sort_col, align=1.0, expand=False):
            col = Gtk.TreeViewColumn(title)
            cell = Gtk.CellRendererText()
            cell.set_property("xalign", align)
            col.pack_start(cell, False)
            col.add_attribute(cell, "text", attr)
            col.set_sort_column_id(sort_col)
            col.set_resizable(True)
            if expand:
                col.set_expand(True)
            else:
                col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
                col.set_fixed_width(120)
            tree.append_column(col)
            return col, cell

        # Name, then Modified, Type, Size, then the metadata columns.
        mt_col, mt_cell = _add_text_col(i18n._("Modified"), COL_MTIME, COL_MTIME)
        mt_col.set_cell_data_func(mt_cell, self._cell_format_mtime, None)
        mt_col.set_fixed_width(140)

        _add_text_col(i18n._("Type"), COL_TYPE, COL_TYPE)
        size_col, size_cell = _add_text_col(i18n._("Size"), COL_SIZE, COL_SIZE)
        size_col.set_cell_data_func(size_cell, self._cell_format_size, None)
        size_col.set_fixed_width(90)

        _add_text_col(i18n._("Permissions"), COL_MODE, COL_MODE)
        _add_text_col(i18n._("Owner"), COL_OWNER, COL_OWNER)
        _add_text_col(i18n._("Group"), COL_GROUP, COL_GROUP)

    def _setup_iconview(self) -> None:
        icons = self._icons
        icons.set_item_orientation(Gtk.Orientation.VERTICAL)
        icons.set_pixbuf_column(COL_ICON_PIXBUF)
        icons.set_text_column(COL_NAME)
        icons.set_spacing(8)
        icons.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        icons.set_item_padding(6)
        if self._mode in ("large", "thumb"):
            icons.set_item_width(140)
        else:
            icons.set_item_width(110)

    # --- checkbox <-> selection sync ------------------------------------------

    def _base_set(self, it, column: int, value) -> None:
        """Write a value through the filter/sort proxies into the base model.

        ``Gtk.TreeModelSort``/``TreeModelFilter`` are read-only; column writes
        must go to :attr:`_base`. Proxying is: filter_iter -> sort_iter -> base.
        """
        try:
            sort_it = self._filter.convert_iter_to_child_iter(it)
            base_it = self._sort.convert_iter_to_child_iter(sort_it)
            self._base.set_value(base_it, column, value)
        except Exception:
            pass

    def _on_check_toggled(self, _cell, path) -> None:
        model = self._tree.get_model()
        it = model.get_iter(path)
        new = not model.get_value(it, COL_CHECKED)
        self._base_set(it, COL_CHECKED, new)
        sel = self._tree.get_selection()
        if new:
            sel.select_path(path)
        else:
            sel.unselect_path(path)

    def _on_selection_changed(self, *_) -> None:
        if self._suppress_sync:
            return
        # Only the tree (list/details/content) modes render checkboxes.
        if self._mode not in ("list", "details", "content"):
            return
        model = self._tree.get_model()
        sel = self._tree.get_selection()
        it = model.get_iter_first()
        while it is not None:
            path = model.get_path(it)
            self._base_set(it, COL_CHECKED, sel.path_is_selected(path))
            it = model.iter_next(it)

    # --- population ---------------------------------------------------------

    def set_entries(self, entries: list[files.FileEntry]) -> None:
        self._base.clear()
        import datetime

        for e in entries:
            icon = _icon_for(e)
            self._base.append([
                e.path, e.display_name, icon, e.is_dir,
                e.size, (e.content_type or e.name),
                e.mtime, files.mode_to_rwx(e.mode) if e.mode else "-",
                e.owner, e.group, _icon_pixbuf(icon), False,
            ])

    def _cell_format_size(self, column, cell, model, it, _data):
        size = model.get_value(it, COL_SIZE)
        cell.set_property("text", format_size(size) if size else "")

    def _cell_format_mtime(self, column, cell, model, it, _data):
        mtime = model.get_value(it, COL_MTIME)
        cell.set_property("text", _fmt_time(mtime))

    def _dirs_first(self, model, iter_a, iter_b, _ud):
        _, order = self._sort.get_sort_column_id()
        asc = order != Gtk.SortType.DESCENDING
        a_dir = model.get_value(iter_a, COL_IS_DIR)
        b_dir = model.get_value(iter_b, COL_IS_DIR)
        if a_dir != b_dir:
            return -1 if a_dir else 1
        col = self._sort.get_sort_column_id()[0]
        a = model.get_value(iter_a, col)
        b = model.get_value(iter_b, col)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            cmp = (a > b) - (a < b)
        else:
            a, b = str(a).lower(), str(b).lower()
            cmp = (a > b) - (a < b)
        return cmp if asc else -cmp

    def _set_sort(self, column: int, ascending: bool = True) -> None:
        self._sort.set_sort_func(column, self._dirs_first, None)
        self._sort.set_sort_column_id(
            column, Gtk.SortType.ASCENDING if ascending else Gtk.SortType.DESCENDING)

    # --- view mode ----------------------------------------------------------

    def set_view(self, mode: str) -> None:
        self._set_view(mode)

    def _set_view(self, mode: str) -> None:
        self._mode = mode
        if mode in _ICON_WIDTHS:
            self._setup_iconview()
            self._stack.set_visible_child_name("icons")
            self._icons.set_item_width(_ICON_WIDTHS[mode])
        else:
            self._stack.set_visible_child_name("tree")

    @property
    def view_mode(self) -> str:
        return self._mode

    def set_show_hidden(self, show: bool) -> None:
        self._show_hidden = show
        self._filter.refilter()

    def set_sort_by(self, column: str, ascending: bool = True) -> None:
        mapping = {"name": COL_NAME, "size": COL_SIZE, "type": COL_TYPE,
                   "mtime": COL_MTIME}
        self._set_sort(mapping.get(column, COL_NAME), ascending)

    # --- filtering ----------------------------------------------------------

    def set_filter(self, text: str) -> None:
        self._filter_text = text.lower()
        self._filter.refilter()

    def _filter_visible(self, model, it, _ud):
        if self._filter_text:
            name = model.get_value(it, COL_NAME).lower()
            if self._filter_text not in name:
                return False
        return True

    # --- selection ----------------------------------------------------------

    def selected_paths(self) -> list[str]:
        paths: list[str] = []
        if self._mode in _ICON_WIDTHS:
            model = self._icons.get_model()
            for path in self._icons.get_selected_items():
                paths.append(_path_of(model, path))
        else:
            sel = self._tree.get_selection()
            model, rows = sel.get_selected_rows()
            for row in rows:
                paths.append(_path_of(model, row))
        return paths

    def select_all(self) -> None:
        self._suppress_sync = True
        try:
            if self._mode in _ICON_WIDTHS:
                model = self._icons.get_model()
                it = model.get_iter_first()
                while it is not None:
                    self._icons.select_path(model.get_path(it))
                    it = model.iter_next(it)
            else:
                self._tree.get_selection().select_all()
        finally:
            self._suppress_sync = False
            self._on_selection_changed()

    def unselect_all(self) -> None:
        self._suppress_sync = True
        try:
            if self._mode in _ICON_WIDTHS:
                self._icons.unselect_all()
            else:
                self._tree.get_selection().unselect_all()
        finally:
            self._suppress_sync = False
            self._on_selection_changed()

    def invert_selection(self) -> None:
        """Select every currently-unselected row and drop the selected ones."""
        self._suppress_sync = True
        try:
            if self._mode in _ICON_WIDTHS:
                model = self._icons.get_model()
                keep = {p.to_string() for p in
                        (model.get_path(i) for i in _iters(model))
                        if p not in self._icons.get_selected_items()}
                self._icons.unselect_all()
                for s in keep:
                    self._icons.select_path(Gtk.TreePath.new_from_string(s))
            else:
                sel = self._tree.get_selection()
                model = self._tree.get_model()
                keep = set()
                for it in _iters(model):
                    p = model.get_path(it)
                    if not sel.path_is_selected(p):
                        keep.add(p.to_string())
                sel.unselect_all()
                for s in keep:
                    sel.select_path(Gtk.TreePath.new_from_string(s))
        finally:
            self._suppress_sync = False
            self._on_selection_changed()

    # --- events -------------------------------------------------------------

    def _row_activated(self, _widget, path, *_):
        # Use the row that was actually activated (double-clicked) rather than
        # the current selection, so activating an unselected row still opens it.
        entry_path = _path_of(self._filter, path)
        if entry_path:
            self._on_activate(entry_path)

    def _button_press(self, widget, event):
        if event.button == Gdk.BUTTON_SECONDARY:
            # Select the item under the cursor (if any) before showing the menu.
            path = ""
            if self._mode in _ICON_WIDTHS:
                pos = self._icons.get_item_at_pos(int(event.x), int(event.y))
                if pos is not None:
                    path = _path_of(self._icons.get_model(), pos)
                    if not self._icons.path_is_selected(pos):
                        self._icons.unselect_all()
                        self._icons.select_path(pos)
                self._on_context_menu(path, bool(path))
            else:
                hit = self._tree.get_path_at_pos(int(event.x), int(event.y))
                if hit is not None:
                    row_path = hit[0]
                    path = _path_of(self._tree.get_model(), row_path)
                    if not self._tree.get_selection().path_is_selected(row_path):
                        self._tree.get_selection().unselect_all()
                        self._tree.get_selection().select_path(row_path)
                self._on_context_menu(path, bool(path))
            return True
        return False


def _path_of(model, path) -> str:
    it = model.get_iter(path)
    return model.get_value(it, COL_PATH)


def _iters(model):
    it = model.get_iter_first()
    while it is not None:
        yield it
        it = model.iter_next(it)


def _fmt_time(epoch: int) -> str:
    if not epoch:
        return ""
    import datetime

    return datetime.datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M")
