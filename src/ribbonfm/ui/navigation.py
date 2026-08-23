"""Navigation logic for the main window.

Kept separate from the window shell so the controller stays small. ``NavigationMixin``
provides the history stack, path canonicalisation and the Glade nav handler methods.
"""

from __future__ import annotations

import os

from ..core import pathutils


class NavigationMixin:
    """Adds navigation state + handlers to :class:`ribbonfm.ui.mainwindow.MainWindow`."""

    def _init_navigation(self, start_path: str) -> None:
        self._history_back: list[str] = []
        self._history_fwd: list[str] = []
        self._current: str = ""
        self._show_hidden = False

    # --- navigation ---------------------------------------------------------

    def navigate(self, path: str) -> None:
        path = self._canonicalize(path)
        if not os.path.isdir(path):
            from ..ui.dialogs import show_error
            from .. import i18n
            show_error(self, i18n._("Cannot open folder"),
                       i18n._("This location is not a readable directory: {path}")
                       .format(path=path))
            return
        if self._current and self._current != path:
            self._history_back.append(self._current)
            self._history_fwd.clear()
        self._current = path
        self._on_navigated(path)

    def _canonicalize(self, path: str) -> str:
        try:
            return os.path.realpath(os.path.expanduser(path))
        except OSError:
            return os.path.expanduser(path)

    def _on_navigated(self, path: str) -> None:
        # Hooks provided by the window.
        self.set_title(f"{self._app_title_text()} - {path}")
        self._address.set_path(path)
        self._update_nav_state()
        hidden = getattr(self, "_file_view", None)
        if hidden is not None and hasattr(hidden, "set_hide_paths"):
            hidden.set_hide_paths([])  # every folder shows all its files
        self._load_directory(path)

    def go_back(self) -> None:
        if self._history_back:
            path = self._history_back.pop()
            self._history_fwd.append(self._current)
            self._current = path
            self._on_navigated(path)

    def go_forward(self) -> None:
        if self._history_fwd:
            path = self._history_fwd.pop()
            self._history_back.append(self._current)
            self._current = path
            self._on_navigated(path)

    def go_up(self) -> None:
        parent = os.path.dirname(self._current.rstrip(os.sep))
        if parent and parent != self._current:
            self.navigate(parent)

    def refresh(self) -> None:
        self._load_directory(self._current)

    def _update_nav_state(self) -> None:
        self._nav_back.set_sensitive(bool(self._history_back))
        self._nav_forward.set_sensitive(bool(self._history_fwd))
        parent = os.path.dirname(self._current.rstrip(os.sep))
        self._nav_up.set_sensitive(bool(parent) and parent != self._current)

    def toggle_show_hidden(self) -> None:
        self._show_hidden = not self._show_hidden
        self._ribbon.set_checked("toggle:show_hidden", self._show_hidden)
        self._load_directory(self._current)

    # --- Glade nav handlers -------------------------------------------------

    def on_nav_back(self, *_):
        self.go_back()

    def on_nav_forward(self, *_):
        self.go_forward()

    def on_nav_up(self, *_):
        self.go_up()

    def on_nav_refresh(self, *_):
        self.refresh()

    def on_address_activate(self, entry):
        self.navigate(entry.get_text())

    def on_toggle_crumb_edit(self, *_):
        self._address.show_entry()

    # --- helpers ------------------------------------------------------------

    def _app_title_text(self) -> str:
        from .. import config
        return config.APP_NAME

    def start_location(self) -> str:
        return str(pathutils.user_home())
