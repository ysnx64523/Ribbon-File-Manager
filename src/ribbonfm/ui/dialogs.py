"""Small modal helper dialogs : errors, confirmations and single-line prompts."""

from __future__ import annotations

from typing import Optional

from gi.repository import Gtk

from .. import i18n


def show_error(parent, message: str, detail: Optional[str] = None) -> None:
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text=message,
    )
    if detail:
        dialog.format_secondary_text(detail)
    dialog.run()
    dialog.destroy()


def show_info(parent, message: str, detail: Optional[str] = None) -> None:
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text=message,
    )
    if detail:
        dialog.format_secondary_text(detail)
    dialog.run()
    dialog.destroy()


def confirm(parent, message: str, detail: Optional[str] = None,
            destructive: bool = False) -> bool:
    """Return ``True`` when the user confirms."""
    if destructive:
        dialog = Gtk.MessageDialog(
            transient_for=parent, modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL, text=message)
    else:
        dialog = Gtk.MessageDialog(
            transient_for=parent, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO, text=message)
    if detail:
        dialog.format_secondary_text(detail)
    response = dialog.run()
    dialog.destroy()
    if destructive:
        return response == Gtk.ResponseType.OK
    return response in (Gtk.ResponseType.YES, Gtk.ResponseType.OK)


def ask_text(parent, title: str, label: str,
             initial: str = "") -> Optional[str]:
    """Prompt for a single line of text (e.g. a new name)."""
    dialog = Gtk.Dialog(title=title, transient_for=parent, modal=True,
                        buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
    dialog.set_default_response(Gtk.ResponseType.OK)
    box = dialog.get_content_area()
    box.set_spacing(6)
    box.set_margin_top(8)
    box.set_margin_bottom(8)
    box.set_margin_start(12)
    box.set_margin_end(12)
    lbl = Gtk.Label(label=label)
    lbl.set_xalign(0)
    box.pack_start(lbl, False, False, 0)
    entry = Gtk.Entry()
    entry.set_text(initial)
    entry.set_activates_default(True)
    box.pack_start(entry, False, False, 0)
    dialog.show_all()
    entry.grab_focus()
    entry.select_region(0, -1)
    response = dialog.run()
    result = entry.get_text().strip()
    dialog.destroy()
    if response == Gtk.ResponseType.OK and result:
        return result
    return None
