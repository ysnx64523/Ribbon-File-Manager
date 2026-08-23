"""A Windows-Explorer-like Ribbon toolbar built from plain GTK3 widgets.

GTK3 has no native Ribbon control, so this is a custom composition:

* A :class:`Gtk.Stack` + :class:`Gtk.StackSwitcher` provides the tab strip.
* Each tab page is a horizontal :class:`Gtk.Box` containing "group" boxes.
* A group is a labelled box that holds either **large** buttons (icon over
  label, like the classic Ribbon) or **small** buttons (icon beside label).
* The whole ribbon can be collapsed/expanded with a toggle arrow.

The button layout is *data driven* (see ribbon_spec.TABS) so translators only need
to provide labelled strings. Actions are dispatched to a callback supplied by the
main window.
"""

from __future__ import annotations

from typing import Callable, Optional

from gi.repository import Gtk, Gdk, Pango

from .. import i18n
from .ribbon_spec import TABS


def _large_button(spec: dict, dispatch: Callable) -> Gtk.Box:
    box = Gtk.Button()
    box.set_relief(Gtk.ReliefStyle.NONE)
    box.set_tooltip_text(i18n._(spec["label_key"]))
    inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    inner.set_homogeneous(False)

    icon = Gtk.Image.new_from_icon_name(spec["icon"], Gtk.IconSize.DND)
    icon.set_pixel_size(32)
    icon.set_size_request(width=48, height=44)
    icon.set_property("margin-top", 4)

    label = Gtk.Label(label=i18n._(spec["label_key"]))
    label.set_line_wrap(True)
    label.set_justify(Gtk.Justification.CENTER)
    label.set_ellipsize(Pango.EllipsizeMode.END)
    label.set_max_width_chars(12)

    inner.pack_start(icon, False, False, 0)
    inner.pack_start(label, False, False, 0)
    box.add(inner)
    if spec.get("check"):
        box._ribbon_check_state = False
        box._ribbon_check_action = spec["action"]
    box._ribbon_action = spec["action"]
    box.connect("clicked", _on_click, dispatch)
    box.get_style_context().add_class("ribbon-large-button")
    return box


def _small_button(spec: dict, dispatch: Callable) -> Gtk.Button:
    box = Gtk.Button()
    box.set_relief(Gtk.ReliefStyle.NONE)
    box.set_tooltip_text(i18n._(spec["label_key"]))
    box.set_image(Gtk.Image.new_from_icon_name(spec["icon"], Gtk.IconSize.MENU))
    box.set_always_show_image(True)
    if spec.get("check"):
        box._ribbon_check_state = False
        box._ribbon_check_action = spec["action"]
    box._ribbon_action = spec["action"]
    box.set_label(i18n._(spec["label_key"]))
    box.connect("clicked", _on_click, dispatch)
    box.get_style_context().add_class("ribbon-small-button")
    return box


def _on_click(button: Gtk.Button, dispatch: Callable) -> None:
    check = getattr(button, "_ribbon_check_state", None)
    if check is not None:
        # Flip the toggle before dispatching so the controller can read it.
        button._ribbon_check_state = not check
        button.get_style_context().remove_class("checked")
        if button._ribbon_check_state:
            button.get_style_context().add_class("checked")
    dispatch(button._ribbon_action)


def _group_widget(group: dict, dispatch: Callable) -> Gtk.Widget:
    frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
    frame.set_property("margin-start", 4)
    frame.set_property("margin-end", 4)

    large_mode = group.get("large", False)
    columns = int(group.get("columns", 0))
    buttons = group["buttons"]

    large_btns = [b for b in buttons if b.get("large", large_mode)]
    small_btns = [b for b in buttons if not b.get("large", large_mode)]

    if columns >= 1 and large_btns and small_btns:
        # Lead-large layout: large button(s) on the left, small buttons in a
        # ``columns``-wide grid on the right (View -> Show/Hide).
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        left.set_halign(Gtk.Align.START)
        for spec in large_btns:
            left.pack_start(_large_button(spec, dispatch), False, False, 0)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        right.set_halign(Gtk.Align.START)
        for i in range(0, len(small_btns), columns):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            row.set_halign(Gtk.Align.START)
            for spec in small_btns[i:i + columns]:
                row.pack_start(_small_button(spec, dispatch), False, False, 0)
            right.pack_start(row, False, False, 0)
        outer.pack_start(left, False, False, 0)
        outer.pack_start(right, False, False, 0)
        frame.pack_start(outer, False, False, 0)
    elif columns >= 1:
        # Arrange the buttons into a 2D grid (``columns`` per row) so wide
        # groups (e.g. the View -> Layout view-mode picker) occupy two rows,
        # and ``columns=1`` stacks them vertically one per row.
        rows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        rows.set_halign(Gtk.Align.START)
        for i in range(0, len(buttons), columns):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            row.set_halign(Gtk.Align.START)
            for spec in buttons[i:i + columns]:
                if spec.get("kind") == "button":
                    widget = _large_button(spec, dispatch) if spec.get("large", large_mode) \
                        else _small_button(spec, dispatch)
                    row.pack_start(widget, False, False, 0)
            rows.pack_start(row, False, False, 0)
        frame.pack_start(rows, False, False, 0)
    else:
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        buttons_box.set_halign(Gtk.Align.START)
        for spec in buttons:
            if spec.get("kind") == "button":
                widget = _large_button(spec, dispatch) if spec.get("large", large_mode) \
                    else _small_button(spec, dispatch)
                buttons_box.pack_start(widget, False, False, 0)
        frame.pack_start(buttons_box, False, False, 0)

    caption = Gtk.Label(label=i18n._(group["label_key"]))
    caption.set_xalign(0)
    caption.set_property("margin-top", 2)
    caption.get_style_context().add_class("ribbon-group-caption")
    frame.pack_start(caption, False, False, 0)

    frame.get_style_context().add_class("ribbon-group")
    sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
    sep.set_property("margin-start", 2)
    sep.set_property("margin-end", 2)
    outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    outer.pack_start(frame, False, False, 0)
    outer.pack_start(sep, False, False, 0)
    return outer


class Ribbon:
    """Builds and manages the Ribbon toolbar."""

    def __init__(self, stack: Gtk.Stack, switcher: Gtk.StackSwitcher,
                 top_row: Gtk.Box, quick_access: Gtk.Box,
                 dispatch: Callable[[str], None],
                 on_collapse: Optional[Callable] = None):
        self._stack = stack
        self._switcher = switcher
        self._top_row = top_row
        self._quick_access = quick_access
        self._dispatch = dispatch
        self._on_collapse = on_collapse
        self._pages: dict[str, Gtk.Box] = {}
        self._collapsed = False
        self._collapse_button: Optional[Gtk.ToggleButton] = None

    def build(self, with_quick_access: bool = True) -> None:
        """Populate the stack and quick-access bar."""
        first = None
        for tab in TABS:
            if tab["id"] == "file":
                # The File entry is a backstage menu, not a ribbon page.
                continue
            page = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            page.get_style_context().add_class("ribbon-page")
            page.set_size_request(-1, 92)  # give the ribbon body a real height
            for group in tab["groups"]:
                page.pack_start(_group_widget(group, self._dispatch),
                                False, False, 0)
            self._stack.add_named(page, tab["id"])
            self._stack.child_set_property(page, "title", i18n._(tab["label_key"]))
            self._stack.child_set_property(page, "name", tab["id"])
            self._pages[tab["id"]] = page
            if first is None:
                first = tab["id"]
        # Prefer "home" as the default tab (like Windows Explorer).
        if "home" in self._pages:
            first = "home"
        self._switcher.set_stack(self._stack)

        self._build_file_backstage()

        if with_quick_access:
            self._build_quick_access()

        self._build_collapse_toggle()

        # Reveal buttons packed into the top row and quick-access bar; the box
        # containers come from Glade and are not auto-shown for new children.
        self._top_row.show_all()
        self._quick_access.show_all()

        # Show the pages and make the first tab active. Without an explicit
        # visible child Gtk.Stack renders nothing, and show_all() is required
        # because programmatically created pages start hidden.
        self._stack.show_all()
        if first:
            self._stack.set_visible_child_name(first)

        # Fix ordering: File backstage leftmost, collapse toggle rightmost, and
        # keep the tab switcher compact (it must not steal the whole row).
        self._switcher.set_hexpand(False)
        if getattr(self, "_file_button", None) is not None:
            self._top_row.reorder_child(self._file_button, 0)
        if getattr(self, "_collapse_button", None) is not None:
            self._top_row.reorder_child(self._collapse_button, -1)

    def _build_file_backstage(self) -> None:
        """File backstage: a menu button (not a ribbon page) with a fly-out."""
        btn = Gtk.MenuButton()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_label(i18n._("ribbon_tab_file"))
        btn.get_style_context().add_class("ribbon-file-button")
        menu = Gtk.Menu()

        term = Gtk.MenuItem(label=i18n._("open_terminal"))
        sub = Gtk.Menu()
        self._add_menu_item(sub, "open_terminal", i18n._("open_terminal"))
        self._add_menu_item(sub, "open_terminal_admin", i18n._("open_terminal_admin"))
        term.set_submenu(sub)
        menu.append(term)

        self._add_menu_item(menu, "options", i18n._("options"))
        self._add_menu_item(menu, "help", i18n._("help"))
        menu.append(Gtk.SeparatorMenuItem())
        self._add_menu_item(menu, "close", i18n._("close"))
        menu.show_all()
        btn.set_popup(menu)
        self._file_menu = menu
        self._file_button = btn
        self._top_row.pack_start(btn, False, False, 0)

    def _add_menu_item(self, menu: Gtk.Menu, action: str, label: str) -> None:
        item = Gtk.MenuItem(label=label)
        item._action = action
        item.connect("activate", lambda w: self._dispatch(w._action))
        menu.append(item)

    def _build_quick_access(self) -> None:
        specs = [
            ("new_folder", "new_folder", "folder-new"),
            ("copy", "copy", "edit-copy"),
            ("paste", "paste", "edit-paste"),
            ("delete", "delete", "user-trash"),
            ("refresh", "refresh", "view-refresh"),
        ]
        for id_, key, icon in specs:
            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_image(Gtk.Image.new_from_icon_name(
                f"{icon}-symbolic", Gtk.IconSize.MENU))
            btn.set_always_show_image(True)
            btn.set_tooltip_text(i18n._(key))
            btn.connect("clicked", _on_click, self._dispatch)
            btn._ribbon_action = id_
            btn.get_style_context().add_class("ribbon-quick-button")
            self._quick_access.pack_start(btn, False, False, 0)

    def _build_collapse_toggle(self) -> None:
        btn = Gtk.ToggleButton()
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_image(Gtk.Image.new_from_icon_name(
            "go-down-symbolic", Gtk.IconSize.MENU))
        btn.set_tooltip_text(i18n._("ribbon_collapse"))
        btn.connect("toggled", self._on_collapse_toggled)
        btn.get_style_context().add_class("ribbon-collapse-button")
        self._collapse_button = btn
        self._top_row.pack_end(btn, False, False, 0)

    def _on_collapse_toggled(self, toggled: Gtk.ToggleButton) -> None:
        self._collapsed = toggled.get_active()
        self._stack.set_visible(not self._collapsed)
        if self._on_collapse:
            self._on_collapse(self._collapsed)

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def set_checked(self, action: str, state: bool) -> None:
        """Reflect an externally-triggered toggle state on a button."""
        pages = self._stack.get_children()
        for page in pages:
            for child in page.get_children():
                for container in child.get_children():
                    self._apply_check(container, action, state)

    def _apply_check(self, container, action: str, state: bool) -> None:
        if hasattr(container, "get_children"):
            for grand in container.get_children():
                self._apply_check(grand, action, state)
        if getattr(container, "_ribbon_check_action", None) == action:
            container._ribbon_check_state = state
            ctx = container.get_style_context()
            ctx.remove_class("checked")
            if state:
                ctx.add_class("checked")
