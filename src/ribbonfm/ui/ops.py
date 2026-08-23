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
        """Open-With chooser: list all system apps + pick a custom program."""
        from gi.repository import Gtk
        import subprocess
        file_ = Gio.File.new_for_path(path)
        apps = list(Gio.AppInfo.get_all()) + \
            list(Gio.AppInfo.get_all_for_type("text/plain") or [])
        seen = set()
        unique = []
        for a in apps:
            key = a.get_id() or a.get_executable()
            if key in seen:
                continue
            seen.add(key)
            unique.append(a)
        apps = sorted(unique, key=lambda a: a.get_name().lower())

        dialog = Gtk.Dialog(transient_for=self, modal=True, title=i18n._("Open With"),
                            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                     i18n._("Open"), Gtk.ResponseType.ACCEPT))
        dialog.set_default_size(520, 460)
        area = dialog.get_content_area()

        header = Gtk.Label(label=i18n._("Choose an application to open {name}")
                           .format(name=os.path.basename(path)))
        header.set_xalign(0)
        header.get_style_context().add_class("prop-key")
        area.pack_start(header, False, False, 6)

        search = Gtk.SearchEntry()
        search.set_placeholder_text(i18n._("Search programs"))
        area.pack_start(search, False, False, 6)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_size_request(-1, 220)
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scroller.add(listbox)
        area.pack_start(scroller, True, True, 6)

        pending = {"prog": None}

        def launch(app) -> None:
            try:
                if callable(app):
                    app()
                else:
                    app.launch([file_], None)
            except Exception as exc:  # noqa: BLE001
                self._show_error(i18n._("Could not open this file"), str(exc))

        def make_row(item):
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            if item == "__browse__":
                icon = Gtk.Image.new_from_icon_name("system-file-manager", Gtk.IconSize.DND)
                lbl = Gtk.Label(label=i18n._("Browse a custom program..."))
                target = lambda: self._pick_program(path, dialog)
                row._launch = target
            else:
                try:
                    icon = Gtk.Image.new_from_gicon(item.get_icon(), Gtk.IconSize.DND)
                except Exception:
                    icon = Gtk.Image.new_from_icon_name("application-x-executable",
                                                        Gtk.IconSize.DND)
                lbl = Gtk.Label(label=item.get_name())
                row._launch = (lambda a=item: a.launch([file_], None))
            lbl.set_xalign(0)
            box.pack_start(icon, False, False, 0)
            box.pack_start(lbl, True, True, 0)
            row.add(box)
            return row

        def populate(query: str) -> None:
            for child in listbox.get_children():
                listbox.remove(child)
            q = query.lower()
            matched = 0
            for app in apps:
                if q and q not in app.get_name().lower():
                    continue
                listbox.add(make_row(app))
                matched += 1
            if not matched and not q:
                pass
            if q and matched == 0:
                none = Gtk.ListBoxRow()
                lbl = Gtk.Label(label=i18n._("No matching application"))
                none.add(lbl)
                listbox.add(none)
            listbox.add(make_row("__browse__"))
            listbox.show_all()

        search.connect("search-changed", lambda e: populate(e.get_text()))
        listbox.connect("row-activated", lambda _lb, row: (
            row._launch(), dialog.response(Gtk.ResponseType.ACCEPT))[0] is None)

        def on_response(d, resp):
            if resp == Gtk.ResponseType.ACCEPT:
                row = listbox.get_selected_row()
                if row is not None:
                    row._launch()
                elif pending["prog"]:
                    pending["prog"]()
            d.destroy()

        dialog.connect("response", on_response)
        populate("")
        dialog.show_all()
        dialog.run()

    def _pick_program(self, path, dialog) -> None:
        """Let the user browse for a custom program to open the file."""
        from gi.repository import Gtk
        chooser = Gtk.FileChooserDialog(
            title=i18n._("Choose a program"), transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                     Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        prog_filter = Gtk.FileFilter()
        prog_filter.set_name(i18n._("Executables"))
        prog_filter.add_pattern("*.desktop")
        prog_filter.add_pattern("*")
        chooser.add_filter(prog_filter)
        if chooser.run() == Gtk.ResponseType.OK:
            prog = chooser.get_filename()
            chooser.destroy()
            if prog:
                try:
                    import subprocess
                    subprocess.Popen([prog, path])
                except Exception as exc:  # noqa: BLE001
                    self._show_error(i18n._("Could not open this file"), str(exc))
                dialog.destroy()
        else:
            chooser.destroy()

    def open_terminal(self) -> None:
        """Launch the system default terminal in the current folder."""
        import shlex
        import shutil
        import subprocess

        terminal = None
        for name in ("x-terminal-emulator", "gnome-terminal", "konsole",
                     "xfce4-terminal", "mate-terminal", "lxterminal",
                     "alacritty", "kitty", "xterm"):
            if shutil.which(name):
                terminal = name
                break
        if not terminal:
            self._show_error(i18n._("Could not open terminal"),
                             i18n._("No supported terminal was found on the system."))
            return

        cwd = self._current
        args: list[str] = [terminal]
        if terminal == "konsole":
            args += ["--workdir", cwd]
        elif terminal == "xterm":
            args += ["-e", f"cd {shlex.quote(cwd)} && exec {os.environ.get('SHELL', 'bash')}"]
        elif terminal == "x-terminal-emulator":
            pass  # inherit cwd via the spawned process
        else:  # gnome-terminal / xfce4-terminal / mate-terminal / lxterminal / ...
            args += ["--working-directory", cwd]
        try:
            subprocess.Popen(args, cwd=cwd)
        except Exception as exc:  # noqa: BLE001
            self._show_error(i18n._("Could not open terminal"), str(exc))

    # --- error/info helpers ------------------------------------------------------

    def _summarize(self, results) -> str:
        return "\n".join(str(r[2]) for r in results[:5])
