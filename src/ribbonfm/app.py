"""GTK application entry point."""

from __future__ import annotations

import argparse
import os
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
        self._dark = False
        self._light_provider = Gtk.CssProvider()
        self._dark_provider = Gtk.CssProvider()
        self._init_theme()
        self._add_system_icon_paths()

    def _init_theme(self) -> None:
        """Load both CSS variants and follow the system light/dark scheme."""
        base = config.resources_dir() / "css"
        try:
            self._light_provider.load_from_path(str(base / "style.css"))
        except GLib.Error as exc:
            print("Could not load light CSS:", exc)
        try:
            self._dark_provider.load_from_path(str(base / "style-dark.css"))
        except GLib.Error as exc:
            print("Could not load dark CSS:", exc)

        self._system_prefers_dark()
        settings = Gtk.Settings.get_default()
        try:
            settings.connect("notify::gtk-application-prefer-dark-theme",
                             self._on_dark_setting_changed)
        except Exception:
            pass
        # Follow OS theme changes live (gtk-theme / color-scheme).
        try:
            gs = Gio.Settings.new("org.gnome.desktop.interface")
            gs.connect("changed::gtk-theme", lambda *_a: self._on_theme_changed())
            gs.connect("changed::color-scheme", lambda *_a: self._on_theme_changed())
        except Exception:
            pass
        self._apply_theme()

    def _detect_dark(self) -> bool:
        """Whether the system is using a dark theme (best effort)."""
        settings = Gtk.Settings.get_default()
        try:
            theme = (settings.get_property("gtk-theme-name") or "").lower()
            if theme.endswith("-dark"):
                return True
        except Exception:
            pass
        try:
            gs = Gio.Settings.new("org.gnome.desktop.interface")
            scheme = (gs.get_string("color-scheme") or "").lower()
            if "dark" in scheme:
                return True
            if (gs.get_string("gtk-theme") or "").lower().endswith("-dark"):
                return True
        except Exception:
            pass
        try:
            if bool(settings.get_property("gtk-application-prefer-dark-theme")):
                return True
        except Exception:
            pass
        return "dark" in os.environ.get("GTK_THEME", "").lower()

    def _system_prefers_dark(self) -> None:
        """Detect the system color scheme and reflect it in GTK settings."""
        dark = self._detect_dark()
        try:
            Gtk.Settings.get_default().set_property(
                "gtk-application-prefer-dark-theme", dark)
        except Exception:
            pass
        self._dark = dark

    def _on_theme_changed(self) -> None:
        self._system_prefers_dark()
        self._apply_theme()

    def _on_dark_setting_changed(self, _settings, _pspec) -> None:
        settings = Gtk.Settings.get_default()
        try:
            self._dark = bool(settings.get_property("gtk-application-prefer-dark-theme"))
        except Exception:
            self._dark = self._dark
        self._apply_theme()

    def _apply_theme(self) -> None:
        screen = Gdk.Screen.get_default()
        if screen is None:
            return
        for provider in (self._light_provider, self._dark_provider):
            Gtk.StyleContext.remove_provider_for_screen(screen, provider)
        provider = self._dark_provider if self._dark else self._light_provider
        Gtk.StyleContext.add_provider_for_screen(
            screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _add_system_icon_paths(self) -> None:
        """Follow the host's icon theme (needed when running from a bundle).

        A self-contained AppImage/deb ships its own GTK but the icon theme should
        come from the system, so append the usual XDG icon directories to the
        default icon theme search path.
        """
        import os
        try:
            theme = Gtk.IconTheme.get_default()
        except Exception:
            return
        for d in ("/usr/share/icons", "/usr/local/share/icons",
                  "/usr/share/pixmaps",
                  os.path.expanduser("~/.local/share/icons"),
                  os.path.expanduser("~/.icons")):
            try:
                if os.path.isdir(d):
                    theme.append_search_path(d)
            except Exception:
                pass

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
