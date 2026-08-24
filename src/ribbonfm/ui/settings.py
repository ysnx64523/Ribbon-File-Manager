"""Settings dialog for RibbonFM (File -> Options)."""

from __future__ import annotations

from gi.repository import Gtk

from .. import i18n
from ..core import settings as app_settings
from .dialogs import show_info


class SettingsDialog:
    def __init__(self, parent, app):
        self._parent = parent
        self._app = app

        self._lang = app_settings.get("lang", "")
        self._theme = app_settings.get("theme", "system")

    def run(self) -> None:
        dialog = Gtk.Dialog(transient_for=self._parent, modal=True,
                            title=i18n._("Options"),
                            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                     Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_default_size(420, -1)
        area = dialog.get_content_area()
        area.set_margin_start(12)
        area.set_margin_end(12)
        area.set_margin_top(12)
        area.set_margin_bottom(12)

        grid = Gtk.Grid()
        grid.set_row_spacing(12)
        grid.set_column_spacing(12)
        area.pack_start(grid, False, False, 0)

        # Language
        grid.attach(Gtk.Label(label=i18n._("Language:")), 0, 0, 1, 1)
        lang_combo = Gtk.ComboBoxText()
        lang_combo.append("system", i18n._("System default"))
        for code in sorted(i18n.available_languages()):
            lang_combo.append(code, code)
        lang_combo.set_active_id(self._lang if self._lang else "system")
        grid.attach(lang_combo, 1, 0, 1, 1)

        # Theme
        grid.attach(Gtk.Label(label=i18n._("Theme:")), 0, 1, 1, 1)
        theme_combo = Gtk.ComboBoxText()
        theme_combo.append("system", i18n._("System"))
        theme_combo.append("light", i18n._("Light"))
        theme_combo.append("dark", i18n._("Dark"))
        theme_combo.set_active_id(self._theme)
        grid.attach(theme_combo, 1, 1, 1, 1)

        note = Gtk.Label(label=i18n._(
            "Language changes take effect after restarting the application."))
        note.set_line_wrap(True)
        note.set_xalign(0)
        note.get_style_context().add_class("security-note")
        area.pack_start(note, False, False, 8)

        dialog.show_all()
        if dialog.run() != Gtk.ResponseType.OK:
            dialog.destroy()
            return
        dialog.destroy()

        new_lang = lang_combo.get_active_id()
        new_theme = theme_combo.get_active_id()
        app_settings.save({"lang": new_lang or "", "theme": new_theme or "system"})

        if new_theme and new_theme != self._theme and self._app is not None:
            self._app.apply_theme_override(new_theme)

        if new_lang and new_lang != "system" and new_lang != self._lang:
            self._app.set_language(new_lang) if self._app else None
            show_info(self._parent, i18n._("Language changed"),
                      i18n._("Please restart the application for the change "
                             "to take effect."))
