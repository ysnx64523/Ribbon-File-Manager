"""Main window controller.

A thin shell that owns the widgets and the action dispatch table. Navigation
state lives in :class:`~ribbonfm.ui.navigation.NavigationMixin` and the mutating
file operations in :class:`~ribbonfm.ui.ops.FileOpsMixin`.
"""

from __future__ import annotations

import os
from typing import Optional

from gi.repository import Gtk, Gio, GLib

from .. import config, i18n
from ..core import files, pathutils, perm, sorts
from ..core.tasks import call_async
from .addressbar import AddressBar
from .dialogs import show_info
from .fileview import FileView
from . import menus
from .navigation import NavigationMixin
from .ops import CLIP_COPY, CLIP_CUT, FileOpsMixin
from .ribbon import Ribbon
from .sidepanel import Sidebar
from .statusbar import StatusBar

_VIEW_MODES = ("huge", "large", "medium", "small", "list", "details",
               "tiles", "content", "thumb")
_SORT_MODES = ("name", "size", "type", "mtime")

# View-tab toggles/placeholders that only flip their checked state (no dialog).
_QUIET_TOGGLES = {
    "add_columns", "fit_columns", "sort_by",
    "selected_items", "hidden_extra",
}


class MainWindow(Gtk.ApplicationWindow, NavigationMixin, FileOpsMixin):
    def __init__(self, application, start_path: Optional[str] = None):
        super().__init__(application=application, title=config.APP_NAME)
        self._builder = Gtk.Builder()
        self._builder.add_from_file(str(config.resources_dir() / "ui" / "mainwindow.glade"))
        self._builder.connect_signals(self)

        self._grouping = False
        self._init_navigation(start_path or self.start_location())
        self._init_clipboard()

        self._adopt_widgets()
        self._build_children()
        self.set_title(config.APP_NAME)
        self.set_default_size(1080, 720)
        self.add(self._builder.get_object("window_root"))
        self.show_all()
        self._apply_pane_visibility()

        self.navigate(start_path or self.start_location())

    # --- widget adoption ----------------------------------------------------

    def _adopt_widgets(self) -> None:
        b = self._builder
        self._quick_access = b.get_object("quick_access_box")
        self._ribbon_switcher = b.get_object("ribbon_switcher")
        self._ribbon_stack = b.get_object("ribbon_stack")
        self._nav_back = b.get_object("nav_back")
        self._nav_forward = b.get_object("nav_forward")
        self._nav_up = b.get_object("nav_up")
        self._nav_refresh = b.get_object("nav_refresh")
        self._crumb_bar = b.get_object("crumb_bar")
        self._address_entry = b.get_object("address_entry")
        self._toggle_crumb = b.get_object("toggle_crumb_edit")
        self._search = b.get_object("search_entry")
        self._sidebar_container = b.get_object("sidebar_container")
        self._view_stack = b.get_object("view_stack")
        self._tree = b.get_object("file_view")
        self._icons = b.get_object("icon_view")
        self._status = b.get_object("status_bar")
        self._info_pane = b.get_object("info_pane")
        self._preview_pane = b.get_object("preview_pane")
        self._preview_image = b.get_object("preview_image")
        self._preview_label = b.get_object("preview_label")
        self._details_pane = b.get_object("details_pane")
        self._details_grid = b.get_object("details_grid")
        self._preview_on = False
        self._details_on = False

    def _build_children(self) -> None:
        self._file_view = FileView(
            self._tree, self._icons, self._view_stack,
            on_activate=self._on_file_activated,
            on_context_menu=self._show_context_menu,
        )
        self._status_bar = StatusBar(self._status)
        self._ribbon = Ribbon(
            self._ribbon_stack, self._ribbon_switcher,
            self._builder.get_object("ribbon_top_row"), self._quick_access,
            self.handle_action, self._on_ribbon_collapse)
        self._ribbon.build()
        self._address = AddressBar(
            self._crumb_bar, self._address_entry, self._toggle_crumb, self.navigate)
        self._sidebar = Sidebar(
            self._sidebar_container, lambda path: self.navigate(path))
        self._search.connect("search-changed", self._on_search_changed)

        self._file_view._tree.get_selection().connect(
            "changed", self._on_view_selection_changed)
        self._file_view._icons.connect(
            "selection-changed", self._on_view_selection_changed)
        self._file_view.set_drop_callback(self._on_drop)
        # Default view toggles: item checkboxes / extensions / hidden items.
        self._file_view.set_checkboxes_visible(False)
        self._file_view.set_show_extensions(False)

    # --- directory loading ----------------------------------------------------

    def _load_directory(self, path: str) -> None:
        call_async(files.list_dir, (path,),
                   kwargs={"show_hidden": self._show_hidden},
                   on_done=self._on_dir_loaded,
                   on_error=self._on_dir_error)

    def _on_dir_loaded(self, entries) -> None:
        in_trash = files.is_trash(self._current)
        if not in_trash:
            entries = [e for e in entries if not
                       (e.name.startswith(".") and not self._show_hidden)]
        if self._grouping:
            entries.sort(key=lambda e: (not e.is_dir, e.content_type or e.name))
        else:
            entries.sort(key=sorts.make_key(self._sort_mode))
        self._file_view.set_entries(entries)
        self._file_view.set_filter(self._search.get_text())
        self._file_view.set_sort_by(self._sort_mode, self._sort_ascending)
        self._file_view.set_show_hidden(self._show_hidden)
        self._update_status(total=len(entries))
        if in_trash:
            self._status_bar.set(
                total=len(entries),
                user=perm.current_user(), is_admin=perm.is_root() or perm.is_admin(),
                location=i18n._("Trash"))

    def _on_dir_error(self, exc) -> None:
        from .dialogs import show_error
        show_error(self, i18n._("Cannot open folder"),
                   i18n._("The folder could not be read. {err}").format(err=exc))

    def _update_status(self, selected: int = 0, total: Optional[int] = None,
                       location: str = "") -> None:
        info = perm.inspect(self._current)
        fs = files.free_space(self._current) if self._current else None
        self._status_bar.set(
            selected=selected, total=total,
            free_space=fs if self._current else None,
            user=info.user_name or perm.current_user(),
            is_admin=perm.is_root() or perm.is_admin(),
            location=location or self._current,
            writable=info.is_writable,
        )

    # --- signal handlers --------------------------------------------------------

    def on_window_destroy(self, *_):
        pass  # GTK handles teardown; kept so connect_signals finds it.

    def _on_search_changed(self, entry) -> None:
        self._file_view.set_filter(entry.get_text())

    # --- right info pane (preview / details) -------------------------------

    def _on_view_selection_changed(self, *_):
        paths = self._file_view.selected_paths()
        if paths:
            self._update_info_pane(paths[0])
        else:
            self._clear_info_pane()

    def _on_drop(self, sources, dest, move) -> None:
        """Copy/move dropped items into ``dest`` (or the current folder)."""
        target = dest or self._current
        if not sources:
            return

        def work():
            results = []
            for s in sources:
                dst = files.unique_path(os.path.join(target, os.path.basename(s)))
                try:
                    if move:
                        files.move(s, dst)
                    else:
                        files.copy(s, dst)
                    results.append((s, None))
                except Exception as exc:  # noqa: BLE001
                    results.append((s, exc))
            return results

        def done(res):
            self.refresh()
            errors = [e for _, e in res if e]
            if errors:
                self._show_error(i18n._("Some items could not be dropped"),
                                 "\n".join(str(e) for e in errors[:5]))

        call_async(work, on_done=done)

    def _toggle_pane(self, kind: str) -> None:
        if kind == "preview":
            self._preview_on = not self._preview_on
        else:
            self._details_on = not self._details_on
        self._preview_pane.set_visible(self._preview_on)
        self._details_pane.set_visible(self._details_on)
        self._info_pane.set_visible(self._preview_on or self._details_on)
        # Keep the ribbon checkbox in sync with the actual pane visibility.
        self._ribbon.set_checked("preview_pane", self._preview_on)
        self._ribbon.set_checked("details_pane", self._details_on)
        self._on_view_selection_changed()

    def _clear_info_pane(self) -> None:
        self._preview_image.clear()
        self._preview_label.set_text("")
        for c in self._details_grid.get_children():
            self._details_grid.remove(c)

    def _update_info_pane(self, path: str) -> None:
        from gi.repository import GdkPixbuf as _GP
        self._preview_label.set_text(os.path.basename(path))
        self._preview_image.clear()
        try:
            entry = files.entry_for_path(path)
        except Exception:  # noqa: BLE001
            entry = None
        ctype = entry.content_type if entry else ""
        if ctype and ctype.startswith("image/"):
            try:
                pix = _GP.Pixbuf.new_from_file_at_scale(path, 240, 240, True)
                self._preview_image.set_from_pixbuf(pix)
            except Exception:  # noqa: BLE001
                self._preview_image.set_from_icon_name("image-x-generic", Gtk.IconSize.DIALOG)
        else:
            icon = "folder" if (entry and entry.is_dir) else "text-x-generic"
            self._preview_image.set_from_icon_name(icon, Gtk.IconSize.DIALOG)
        self._fill_details(path)

    def _fill_details(self, path: str) -> None:
        grid = self._details_grid
        for c in list(grid.get_children()):
            grid.remove(c)
        try:
            entry = files.entry_for_path(path)
        except Exception:  # noqa: BLE001
            entry = None
        hint = perm.inspect(path)
        rows = [
            (i18n._("Name"), os.path.basename(path)),
            (i18n._("Type"), (entry.content_type if entry else "") or ""),
            (i18n._("Size"), _size_human(entry.size) if entry else ""),
            (i18n._("Modified"), _ts(entry.mtime) if entry else ""),
            (i18n._("Permissions"), hint.rwx),
            (i18n._("Owner"), hint.user_name),
            (i18n._("Group"), hint.group_name),
            (i18n._("Path"), path),
        ]
        row = 0
        for key, val in rows:
            k = Gtk.Label(label=key)
            k.set_xalign(0)
            k.get_style_context().add_class("prop-key")
            v = Gtk.Label(label=val or "—")
            v.set_xalign(0)
            v.set_selectable(True)
            v.set_ellipsize(3)
            v.set_hexpand(True)
            grid.attach(k, 0, row, 1, 1)
            grid.attach(v, 1, row, 1, 1)
            row += 1
        grid.show_all()

    def _on_file_activated(self, path: str) -> None:
        self.open_path(path)

    def _on_ribbon_collapse(self, collapsed: bool) -> None:
        self.queue_draw()

    # --- action dispatch -----------------------------------------------------------

    def handle_action(self, action: str) -> None:
        if action.startswith("view:"):
            key = action.split(":", 1)[1]
            if key in _VIEW_MODES:
                self._file_view.set_view(key)
            return
        if action.startswith("sort:"):
            key = action.split(":", 1)[1]
            if key in _SORT_MODES:
                self._set_sort_mode(key)
            return
        if action.startswith("toggle:"):
            key = action.split(":", 1)[1]
            if key == "show_hidden":
                self.toggle_show_hidden()
            elif key == "grouping":
                self._grouping = not self._grouping
                self.refresh()
            elif key == "nav_pane":
                self._toggle_nav_pane()
            elif key == "preview_pane":
                self._toggle_pane("preview")
            elif key == "details_pane":
                self._toggle_pane("details")
            return

        if action in ("preview_pane", "details_pane"):
            self._toggle_pane("preview" if action == "preview_pane" else "details")
            return

        if action in ("checkboxes", "file_extensions"):
            if action == "checkboxes":
                self._toggle_checkboxes()
            else:
                self._toggle_extensions()
            return

        # In the Trash, creation/clipboard actions are disabled (like Windows).
        if files.is_trash(self._current) and action in (
                "new_folder", "new_file", "cut", "copy", "paste", "rename",
                "move_to", "copy_to", "pin_to_quick_access"):
            show_info(self, i18n._("Not available in Trash"),
                      i18n._("This action is not available for items in the Trash."))
            return

        if action in _QUIET_TOGGLES:
            # Toggle-only / placeholder View buttons: their checked state already
            # flipped; do not pop a dialog.
            return

        table = self._action_table()
        handler = table.get(action)
        if handler:
            handler()
        else:
            show_info(self, i18n._("Not implemented yet"),
                      i18n._("The '{action}' action is a placeholder.").format(action=action))

    def _action_table(self) -> dict:
        return {
            "new_folder": self.new_folder,
            "new_file": self.new_file,
            "cut": lambda: self._set_clip(CLIP_CUT),
            "copy": lambda: self._set_clip(CLIP_COPY),
            "paste": self.paste,
            "move_to": lambda: self._set_clip(CLIP_CUT),
            "copy_to": lambda: self._set_clip(CLIP_COPY),
            "pin_to_quick_access": self._pin_to_quick_access,
            "delete": self.delete,
            "delete_permanent": self.delete_permanent,
            "rename": self.rename,
            "properties": self.properties,
            "refresh": self.refresh,
            "select_all": self._file_view.select_all,
            "select_none": self._file_view.unselect_all,
            "invert_select": self._file_view.invert_selection,
            "hide_selected": self._hide_selected,
            "open": self.open_selection,
            "edit": self.open_selection_with,
            "open_with": self.open_selection_with,
            "open_terminal": self.open_terminal,
            "open_terminal_admin": self._open_terminal_admin,
            "restore": self.restore,
            "empty_trash": self.empty_trash,
            "trash_delete_permanent": self.trash_delete_permanent,
            "options": self._options,
            "help": self._help,
            "close": self.close,
        }

    def _options(self) -> None:
        from .settings import SettingsDialog
        SettingsDialog(self, self.get_application()).run()

    def _toggle_nav_pane(self) -> None:
        self._sidebar_container.set_visible(not self._sidebar_container.get_visible())

    def _toggle_checkboxes(self) -> None:
        show = not self._file_view._check_col.get_visible()
        self._file_view.set_checkboxes_visible(show)
        self._ribbon.set_checked("checkboxes", show)

    def _toggle_extensions(self) -> None:
        show = not self._file_view._show_ext
        self._file_view.set_show_extensions(show)
        self._ribbon.set_checked("file_extensions", show)

    def _apply_pane_visibility(self) -> None:
        """Set the right info pane visibility from the current flags."""
        self._preview_pane.set_visible(self._preview_on)
        self._details_pane.set_visible(self._details_on)
        self._info_pane.set_visible(self._preview_on or self._details_on)

    def _hide_selected(self) -> None:
        """Hide the currently selected items from the view."""
        paths = self._file_view.selected_paths()
        if not paths:
            return
        cur = getattr(self._file_view, "_hide_set", set())
        self._file_view.set_hide_paths(cur | set(paths))

    def _open_terminal_admin(self) -> None:
        show_info(self, i18n._("Administrator terminal"),
                  i18n._("This would open a terminal with elevated privileges."))

    def _help(self) -> None:
        from gi.repository import GdkPixbuf  # noqa: F401
        try:
            dialog = Gtk.AboutDialog(
                transient_for=self,
                program_name=config.APP_NAME,
                version=_app_version(),
                comments=i18n._("A cross-platform Ribbon-style file manager."),
                license_type=Gtk.License.APACHE_2_0,
                website="https://github.com/ysnx64523/Ribbon-File-Manager",
            )
            dialog.run()
            dialog.destroy()
        except Exception as exc:  # noqa: BLE001
            show_info(self, config.APP_NAME, str(exc))

    def _pin_to_quick_access(self) -> None:
        name = os.path.basename(self._current.rstrip(os.sep)) or self._current
        self._sidebar.add_bookmark(name, self._current)

    def _set_sort_mode(self, key: str) -> None:
        self._sort_mode = key
        self._file_view.set_sort_by(key, self._sort_ascending)
        self.refresh()

    # --- status helpers -------------------------------------------------------------

    def _show_error(self, message, detail=None) -> None:
        from .dialogs import show_error
        show_error(self, message, detail)

    def _show_info(self, message, detail=None) -> None:
        from .dialogs import show_info
        show_info(self, message, detail)

    # --- context menu ------------------------------------------------------------------

    def _show_context_menu(self, path: str, on_item: bool) -> None:
        if files.is_trash(self._current):
            if on_item and path:
                menu = menus.build_trash_item_menu(path, self.handle_action)
            else:
                menu = menus.build_trash_background_menu(self.handle_action)
        elif on_item and path:
            menu = menus.build_item_menu(path, self._file_view.selected_paths(),
                                         self.handle_action)
        else:
            menu = menus.build_background_menu(self._current, self.handle_action)
        menu.show_all()
        menu.popup_at_pointer(None)


# Keep default state attributes available (set by mixins at runtime).
MainWindow._sort_mode = "name"
MainWindow._sort_ascending = True


def _app_version() -> str:
    """Current app version, derived from the git tag (see ribbonfm.__version__)."""
    try:
        from .. import __version__
        return str(__version__)
    except Exception:
        return "0.0.0"


def _size_human(size: int) -> str:
    s = float(size)
    units = ["B", "KB", "MB", "GB", "TB"]
    u = 0
    while s >= 1024 and u < len(units) - 1:
        s /= 1024
        u += 1
    return f"{int(s)} {units[u]}" if u == 0 else f"{s:.1f} {units[u]}"


def _ts(epoch: int) -> str:
    if not epoch:
        return ""
    import datetime

    return datetime.datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M")
