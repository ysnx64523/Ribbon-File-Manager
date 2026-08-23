"""Bottom status bar.

Shows the current user + privilege state, the selection count, the item count
and the amount of free space on the current file system. The strings are
localised and refreshed from the controller.
"""

from __future__ import annotations

from typing import Optional

from gi.repository import Gtk

from .. import i18n


class StatusBar:
    def __init__(self, statusbar: Gtk.Statusbar):
        self._sb = statusbar
        self._context_id = statusbar.get_context_id("ribbonfm")
        self._clear()

    def _clear(self) -> None:
        self._sb.remove_all(self._context_id)

    def set(self, *, selected: int = 0, total: Optional[int] = None,
            free_space: Optional[int] = None,
            user: str = "", is_admin: bool = False,
            location: Optional[str] = None,
            writable: bool = True) -> None:
        self._clear()
        parts: list[str] = []

        if location is not None:
            parts.append(i18n._("Location: {loc}").format(loc=location))

        if total is not None:
            parts.append(i18n._("{n} items").format(n=_n(total)))

        if selected:
            parts.append(i18n._("{n} selected").format(n=_n(selected)))

        if free_space is not None:
            parts.append(i18n._("Free space: {size}").format(
                size=format_size(free_space)))

        priv = i18n._("User: {user}").format(user=user or "?").replace("?", user or "?")
        if is_admin:
            priv += " (" + i18n._("administrator") + ")"
        parts.append(priv)

        if not writable:
            parts.append(i18n._("Read only"))

        self._sb.push(self._context_id, " · ".join(parts))


def _n(count: int) -> str:
    """Local (non-fractional) number formatting with thousand separators."""
    return f"{count:,}"


def format_size(size: int | float) -> str:
    """Human readable size (kept here to avoid a UI dependency elsewhere)."""
    size = float(size)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit = 0
    while size >= 1024 and unit < len(units) - 1:
        size /= 1024
        unit += 1
    if unit == 0:
        return f"{int(size)} {units[unit]}"
    return f"{size:.1f} {units[unit]}"
