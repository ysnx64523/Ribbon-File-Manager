"""GTK application entry point."""

from __future__ import annotations

import argparse
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, Gio, GLib  # noqa: E402

from . import config, i18n  # noqa: E402
from .ui.mainwindow import MainWindow  # noqa: E402


class RibbonFMApp(Gtk.Application):
    def __init__(self, start_path: str | None = None):
        super().__init__(application_id=config.APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self._start_path = start_path
        self._window: "MainWindow | None" = None
        self._apply_css()

    def _apply_css(self) -> None:
        provider = Gtk.CssProvider()
        css_file = config.resources_dir() / "css" / "style.css"
        try:
            provider.load_from_path(str(css_file))
            screen = Gdk.Screen.get_default()
            if screen is None:
                return
            Gtk.StyleContext.add_provider_for_screen(
                screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except GLib.Error as exc:
            print("Could not load CSS:", exc)

    def do_activate(self, *_):
        window = self.props.active_window
        if not window:
            window = self._create_window()
        window.present()

    def _create_window(self) -> MainWindow:
        window = MainWindow(self, self._start_path)
        self._window = window
        return window

    def reload_language(self, language: str) -> None:
        """Switch language, then ask the user to restart."""
        i18n.set_language(language)
        if self._window:
            from .ui.dialogs import show_info
            show_info(self._window, i18n._("Language changed"),
                      i18n._("Please restart the application for the change "
                             "to take effect."))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=config.APP_NAME,
                                     description=config.APP_NAME)
    parser.add_argument("path", nargs="?", default=None,
                        help="folder to open on startup")
    parser.add_argument("--lang", default=None,
                        help="force a UI language (e.g. zh-CN)")
    args = parser.parse_args(argv)

    i18n.init(args.lang)
    start = args.path or str(Path.home())
    app = RibbonFMApp(start)
    return app.run(argv)
