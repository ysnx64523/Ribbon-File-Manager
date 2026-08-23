"""File operations exposed to the controller.

``FileOpsMixin`` groups every destructive/mutating action (clipboard, create,
delete, rename, properties, open-with) so the main window is a thin dispatcher.
All blocking work is marshalled to the worker pool via :func:`call_async`.
"""

from __future__ import annotations

import os

from gi.repository import Gio

from .. import i18n
from ..core import files
from ..core.tasks import call_async

CLIP_NONE = 0
CLIP_COPY = 1
CLIP_CUT = 2


class FileOpsMixin:
    def _init_clipboard(self) -> None:
        self._clip_paths: list[str] = []
        self._clip_mode = CLIP_NONE

    # --- clipboard ------------------------------------------------------------

    def _set_clip(self, mode: int) -> None:
        paths = self._file_view.selected_paths()
        if not paths:
            return
        self._clip_paths = paths
        self._clip_mode = mode

    def paste(self) -> None:
        if not self._clip_paths or self._clip_mode == CLIP_NONE:
            return
        cut = self._clip_mode == CLIP_CUT

        def work():
            results = []
            for src in self._clip_paths:
                dst = files.unique_path(self._destination_for(src))
                try:
                    if cut:
                        files.move(src, dst, overwrite=False)
                    else:
                        files.copy(src, dst, overwrite=False)
                    results.append((src, dst, None))
                except Exception as exc:  # noqa: BLE001
                    results.append((src, None, exc))
            return results

        def done(results):
            self._clip_mode = CLIP_NONE
            self._load_directory(self._current)
            errors = [r for r in results if r[2]]
            if errors:
                self._show_error(i18n._("Some items were not pasted"),
                                 self._summarize(errors))
            else:
                self._show_info(i18n._("Pasted {n} item(s)").format(n=len(results)))

        call_async(work, on_done=done)

    def _destination_for(self, path: str) -> str:
        return os.path.join(self._current, os.path.basename(path))

    # --- create / destruct ----------------------------------------------------

    def new_folder(self) -> None:
        from .dialogs import ask_text
        name = ask_text(self, i18n._("New Folder"), i18n._("Folder name:"),
                        i18n._("New Folder"))
        if not name:
            return
        path = files.unique_path(os.path.join(self._current, name))
        call_async(files.make_directory, (path,), on_done=(lambda _: self.refresh()),
                   on_error=lambda e: self._show_error(
                       i18n._("Could not create folder"), str(e)))

    def new_file(self) -> None:
        from .dialogs import ask_text
        name = ask_text(self, i18n._("New File"), i18n._("File name:"),
                        i18n._("New File.txt"))
        if not name:
            return
        path = files.unique_path(os.path.join(self._current, name))
        call_async(files.make_file, (path,), on_done=(lambda _: self.refresh()),
                   on_error=lambda e: self._show_error(
                       i18n._("Could not create file"), str(e)))

    def rename(self) -> None:
        from .dialogs import ask_text
        paths = self._file_view.selected_paths() or ([self._current] if self._current else [])
        if not paths:
            return
        path = paths[0]
        new = ask_text(self, i18n._("Rename"), i18n._("New name:"),
                       os.path.basename(path))
        if not new:
            return
        new_path = os.path.join(os.path.dirname(path), new)
        call_async(files.rename, (path, new_path), on_done=(lambda _: self.refresh()),
                   on_error=lambda e: self._show_error(
                       i18n._("Rename failed"), str(e)))

    def delete(self) -> None:
        from .dialogs import confirm
        paths = self._file_view.selected_paths()
        if not paths:
            return
        if not confirm(self, i18n._("Move {n} item(s) to Trash?").format(n=len(paths)),
                       destructive=True):
            return
        self._run_for_each(paths, "trash")

    def delete_permanent(self) -> None:
        from .dialogs import confirm
        paths = self._file_view.selected_paths()
        if not paths:
            return
        if not confirm(self, i18n._("Permanently delete {n} item(s)?").format(n=len(paths)),
                       i18n._("This cannot be undone."), destructive=True):
            return
        self._run_for_each(paths, "delete")

    def _run_for_each(self, paths, op):
        def work():
            errors = []
            ok = 0
            for p in paths:
                try:
                    if op == "trash" and files.trash(p):
                        ok += 1
                    elif op == "delete":
                        files.delete_permanent(p)
                        ok += 1
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{p}: {exc}")
            return ok, errors

        def done(res):
            ok, errors = res
            self.refresh()
            if errors:
                msg = (i18n._("Some items could not be moved to Trash")
                       if op == "trash" else i18n._("Some items could not be deleted"))
                self._show_error(msg, "\n".join(errors[:5]))

        call_async(work, on_done=done)

    def properties(self) -> None:
        paths = self._file_view.selected_paths() or ([self._current] if self._current else [])
        if not paths:
            return
        from .propsdialog import PropertiesDialog
        PropertiesDialog(self, paths[0]).run()

    # --- opening files ----------------------------------------------------------

    def open_selection(self) -> None:
        paths = self._file_view.selected_paths() or ([self._current] if self._current else [])
        if paths:
            self.open_path(paths[0])

    def open_path(self, path: str) -> None:
        entry = files.entry_for_path(path)
        if entry.is_dir:
            self.navigate(path)
        else:
            self.open_with_default(path)

    def open_with_default(self, path: str) -> None:
        try:
            Gio.AppInfo.launch_default_for_uri(
                Gio.File.new_for_path(path).get_uri(), None)
        except Exception as exc:  # noqa: BLE001
            self._show_error(i18n._("Could not open this file"), str(exc))

    def open_selection_with(self) -> None:
        paths = self._file_view.selected_paths()
        if paths:
            self.open_with_dialog(paths[0])

    def open_with_dialog(self, path: str) -> None:
        file_ = Gio.File.new_for_path(path)
        ctype = file_.query_info("standard::content-type").get_content_type()
        apps = Gio.AppInfo.get_all_for_type(ctype)
        from gi.repository import Gtk
        menu = Gtk.Menu()
        for app in apps:
            item = Gtk.MenuItem(label=app.get_name())
            item.connect("activate", lambda _, a=app: a.launch([file_], None))
            menu.append(item)
        if not apps:
            self._show_info(i18n._("No application found"),
                            i18n._("There is no registered application for this type."))
            return
        menu.show_all()
        menu.popup_at_pointer(None)

    def open_terminal(self) -> None:
        try:
            Gio.AppInfo.launch_default_for_uri(
                Gio.File.new_for_path(self._current).get_uri(), None)
        except Exception as exc:  # noqa: BLE001
            self._show_error(i18n._("Could not open terminal"), str(exc))

    # --- error/info helpers ------------------------------------------------------

    def _summarize(self, results) -> str:
        return "\n".join(str(r[2]) for r in results[:5])
