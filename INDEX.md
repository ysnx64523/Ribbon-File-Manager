# Ribbon-File-Manager — Auditable Code INDEX

Hierarchical file-tree navigation for the whole repository. A single root
`INDEX.md` lists every source file and its responsibility; the **machine
generated inventory** (bottom) keeps the symbol/file table fresh without manual
effort. No vector DB or embeddings are required to use it.

## Purpose

RibbonFM is a cross-platform file manager with a Windows-Explorer-like Ribbon
toolbar, written in Python with **PyGObject (GTK3)**. The core file-system logic
lives in `src/ribbonfm/core` (no GTK widgets — unit-testable), and the GTK UI in
`src/ribbonfm/ui` (widgets + a thin controller). Privileged operations are always
escalated via the OS secure mechanism; the app never runs elevated.

## Files

| File | Current responsibility |
|---|---|
| `src/ribbonfm/app.py` | `RibbonFMApp(Gtk.Application)`: owns the window, loads CSS, exposes `reload_language()`; `main()` is the CLI/console entry point. |
| `src/ribbonfm/__main__.py` | `python -m ribbonfm` wrapper that calls `app.main()`. |
| `src/ribbonfm/config.py` | Constants (`APP_ID`, `APP_NAME`, gettext domain) and `resources_dir()` path discovery (src checkout vs installed). |
| `src/ribbonfm/i18n.py` | `gettext` setup; `init()`/`set_language()`; language-code normalisation (`zh-CN` ↔ `zh_CN`); catalog discovery under `resources/locale`. |
| `src/ribbonfm/core/pathutils.py` | Cross-platform path helpers: `Gio.File`↔`Path`, special user dirs, hidden-path heuristic, platform flags (`IS_LINUX/...`). |
| `src/ribbonfm/core/files.py` | `Gio.File` operations (list/enumerate, copy, move, trash, delete, rename, set perms/owner, free space) and the `FileEntry` dataclass; `mode_to_rwx`. |
| `src/ribbonfm/core/perm.py` | Permission checks + privilege escalation. `inspect()`→`PermHint`; `chmod`/`chown` escalate via `pkexec` (Linux) / `runas` (Win) / osascript (macOS). Handles `777` with a warning, read-only detection. |
| `src/ribbonfm/core/mounts.py` | `Gio.VolumeMonitor` wrappers → `MountInfo` for the sidebar Devices section. |
| `src/ribbonfm/core/sorts.py` | `make_key(column)` directory-first sort primitives (name/size/type/mtime). |
| `src/ribbonfm/core/tasks.py` | `call_async()` — bounded `ThreadPoolExecutor` (max 4) + `GLib.idle_add` marshalling so blocking I/O never freezes the UI. |
| `src/ribbonfm/ui/mainwindow.py` | `MainWindow(Gtk.ApplicationWindow, NavigationMixin, FileOpsMixin)`: thin controller — loads the `.glade`, adopts widgets, builds children, and dispatches actions. |
| `src/ribbonfm/ui/navigation.py` | `NavigationMixin`: back/forward/up history, path canonicalisation, `navigate()`; the Glade nav/address signal handlers. |
| `src/ribbonfm/ui/ops.py` | `FileOpsMixin`: clipboard (cut/copy/paste), new folder/file, rename, trash/permanent delete, properties, open/open-with/terminal. |
| `src/ribbonfm/ui/ribbon.py` | `Ribbon` widget: `Gtk.Stack`+`Gtk.StackSwitcher` tab strip, large/small buttons, group boxes, collapse toggle, quick-access bar. |
| `src/ribbonfm/ui/ribbon_spec.py` | Declarative `TABS`/`_group`/`_btn` data — the Ribbon layout; add buttons/tabs here, not in widget code. |
| `src/ribbonfm/ui/addressbar.py` | `AddressBar`: breadcrumb buttons + toggle to an editable `Gtk.Entry`. |
| `src/ribbonfm/ui/sidepanel.py` | `Sidebar`: Places/Bookmarks/Devices/Network tree, bookmark persistence, context menu. |
| `src/ribbonfm/ui/fileview.py` | `FileView`: shared `Gtk.ListStore` for `Gtk.TreeView` (details) + `Gtk.IconView` (icons); sorting, name filter, selection; icon/pixbuf cache. |
| `src/ribbonfm/ui/statusbar.py` | `StatusBar` (selection/count/free-space/user + read-only state) and `format_size()`. |
| `src/ribbonfm/ui/menus.py` | Right-click menus: `build_item_menu` (item) and `build_background_menu` (folder background). |
| `src/ribbonfm/ui/dialogs.py` | `show_error`/`show_info`/`confirm`/`ask_text` modal dialogs. |
| `src/ribbonfm/ui/propsdialog.py` | `PropertiesDialog`: metadata + POSIX mode/owner + an escalation-aware permission editor. |
| `resources/ui/mainwindow.glade` / `resources/css/style.css` / `resources/locale/**` | UI layout (Gtk.Builder), theme CSS, compiled `.mo` catalogs. |
| `tools/gen_po.py` | Maintains `po/<lang>.po` + compiles `.mo` into `resources/locale`. |
| `tools/gen_index.py` | Regenerates the machine inventory section in this file. |
| `tests/test_core.py` | Non-GUI unit tests for core files/perm/pathutils/sorts. |
| `pack/` | Packaging: Flatpak manifest, AppImage build, MSYS2+PyInstaller spec + UAC helper, macOS Homebrew/py2app docs. |
| `doc/` | `INSTALL.md`, `ARCHITECTURE.md`, `SECURITY.md` (auth & privilege escalation). |

## Retrieval lifecycle

```text
launch → app.main() → i18n.init
       → RibbonFMApp.do_activate → MainWindow (glade + children)
       → navigate(start) → canonicalize → list_dir (async)

user action → handle_action(action)
       ├─ view:/sort:/toggle:  → fileview.set_view / set_sort_by / toggle_show_hidden
       └─ file op (new/copy/paste/delete/rename/props) → FileOpsMixin + call_async
                                                       → idle_add → refresh UI
```

- Directory listing, copy, move, trash and delete all run on the worker pool
  (`core.tasks`), so the main loop stays responsive.
- The controller `handle_action(action)` is the single dispatch point shared by
  the Ribbon, the quick-access bar and the context menus.
- `perm.inspect()` is used for status display and to decide whether an operation
  needs `pkexec`/UAC escalation.

## Entry points

- Console script: `ribbonfm` → `ribbonfm.app:main` (see the generated inventory below).
- `python -m ribbonfm [path] [--lang LANG]`.

## Deliberate boundaries

- GTK3/PyGObject only: no Qt, no GTK4, no vector/semantic search.
- The app never runs with elevated privileges; it performs short, well-scoped
  privileged actions via `pkexec`/`runas` and releases them immediately.
- No network/cloud features; the Network sidebar entry is a placeholder.
- Icon/tree rendering is the FileView's job; all file-system knowledge stays in
  `core/` so it remains unit-testable without a display.

<!-- @@INVENTORY:START@@ -->
## Generated inventory (auto-updated)

> Regenerate with `python tools/gen_index.py`. The table below is produced
> mechanically so the curated narrative above never goes stale.

| File | Lines | Symbols `defs`/`class` |
| --- | ---: | --- |
| `src/ribbonfm/__init__.py` | 21 | — |
| `src/ribbonfm/__main__.py` | 6 | — |
| `src/ribbonfm/app.py` | 210 | RibbonFMApp, main |
| `src/ribbonfm/config.py` | 43 | resources_dir |
| `src/ribbonfm/core/__init__.py` | 1 | — |
| `src/ribbonfm/core/files.py` | 366 | is_trash, FileEntry, mode_to_rwx, _str_of, _uint_of, _entry_from_info, list_dir, list_trash, entry_for_uri, restore, trash_delete, empty_trash, entry_for_path, rename, make_directory, make_file, copy, move, delete_permanent, trash, set_permissions, set_owner, is_writable, is_readable, free_space, unique_path, resolve_symlink |
| `src/ribbonfm/core/mounts.py` | 178 | MountInfo, list_mounts, _os_mount_points, mount_volume, _removable, is_mount_point |
| `src/ribbonfm/core/pathutils.py` | 115 | user_home, _special_dir, user_desktop, user_documents, user_downloads, user_music, user_pictures, user_videos, special_navigation, path_to_file, file_to_path, is_hidden_path, display_name, home_or_root, normalize, kind_label |
| `src/ribbonfm/core/perm.py` | 338 | UnsupportedError, PermHint, is_root, current_user, is_admin, _win_admin, _mode_str, inspect, _win_writable, can_no_privilege, _pkexec_ok, escalate, _escalate_tokens, chmod, chown, write_protected |
| `src/ribbonfm/core/settings.py` | 44 | settings_path, load, get, save |
| `src/ribbonfm/core/sorts.py` | 21 | make_key |
| `src/ribbonfm/core/tasks.py` | 86 | call_async, _log_error, call_async_chain |
| `src/ribbonfm/i18n.py` | 217 | _locale_dir, _discover, available_languages, current_language, _make_translator, _candidates, _install_system, os_lang, _windows_lang, _first_available, init, _activate, set_language |
| `src/ribbonfm/ui/__init__.py` | 7 | — |
| `src/ribbonfm/ui/addressbar.py` | 95 | AddressBar |
| `src/ribbonfm/ui/dialogs.py` | 90 | show_error, show_info, confirm, ask_text |
| `src/ribbonfm/ui/fileview.py` | 615 | _icon_for, _size_str, _icon_pixbuf, format_size, FileView, _path_of, _iters, _fmt_time |
| `src/ribbonfm/ui/mainwindow.py` | 495 | MainWindow, _app_version, _size_human, _ts |
| `src/ribbonfm/ui/menus.py` | 120 | build_item_menu, build_background_menu, build_trash_item_menu, build_trash_background_menu, popup |
| `src/ribbonfm/ui/navigation.py` | 134 | NavigationMixin |
| `src/ribbonfm/ui/ops.py` | 453 | FileOpsMixin |
| `src/ribbonfm/ui/propsdialog.py` | 291 | PropertiesDialog, _size_human |
| `src/ribbonfm/ui/ribbon.py` | 313 | _large_button, _small_button, _on_click, _group_widget, Ribbon |
| `src/ribbonfm/ui/ribbon_spec.py` | 143 | _btn, _group |
| `src/ribbonfm/ui/settings.py` | 79 | SettingsDialog |
| `src/ribbonfm/ui/sidepanel.py` | 253 | Sidebar, _human_label |
| `src/ribbonfm/ui/statusbar.py` | 73 | StatusBar, _n, format_size |
| `tools/gen_index.py` | 155 | _symbols, _class_methods, _scan, _entry_points, _render, build, update, main |
| `tools/gen_po.py` | 481 | _concat_msgid, _project_version, generate, _parse_quoted, _escape, compile_mo, _ensure_pot, main |
| `tests/test_core.py` | 127 | ModeTest, ListingTest, SortTest, PermTest, PathTest, I18nTest |

### Entry points
- console script: ``ribbonfm`` -> ``ribbonfm.app:main``
- ``python -m ribbonfm`` (via src/ribbonfm/__main__.py)

### Notable methods
- `src/ribbonfm/app.py`: RibbonFMApp.__init__, RibbonFMApp._init_theme, RibbonFMApp._poll_theme, RibbonFMApp._detect_dark, RibbonFMApp._system_prefers_dark, RibbonFMApp._on_theme_changed, RibbonFMApp._on_dark_setting_changed, RibbonFMApp._apply_theme, RibbonFMApp._add_system_icon_paths, RibbonFMApp.apply_theme_override, RibbonFMApp.set_language, RibbonFMApp.do_activate, RibbonFMApp._create_window, RibbonFMApp.reload_language
- `src/ribbonfm/core/files.py`: FileEntry.is_file
- `src/ribbonfm/core/mounts.py`: MountInfo.is_valid
- `src/ribbonfm/core/perm.py`: PermHint.warning
- `src/ribbonfm/ui/addressbar.py`: AddressBar.__init__, AddressBar._on_toggle, AddressBar._set_edit_mode, AddressBar._on_entry_activate, AddressBar.set_path, AddressBar._rebuild_crumbs, AddressBar._add_separator, AddressBar._add_crumb, AddressBar._on_crumb_click, AddressBar.show_entry
- `src/ribbonfm/ui/fileview.py`: FileView.__init__, FileView.set_drop_callback, FileView._enable_drag_drop, FileView._drag_data_get, FileView._drop_dest, FileView._drag_data_received, FileView._pixbuf_col, FileView._setup_tree, FileView._setup_iconview, FileView._base_set, FileView._on_check_toggled, FileView._on_selection_changed, FileView.set_entries, FileView._cell_format_size, FileView._cell_format_mtime, FileView._cell_format_name, FileView.set_checkboxes_visible, FileView.set_show_extensions, FileView._dirs_first, FileView._set_sort, FileView.set_view, FileView._set_view, FileView.zoom, FileView._on_scroll, FileView._rasterize_icons, FileView.view_mode, FileView.set_show_hidden, FileView.set_sort_by, FileView.set_filter, FileView._filter_visible, FileView.set_hide_paths, FileView.selected_paths, FileView.select_all, FileView.unselect_all, FileView.invert_selection, FileView._row_activated, FileView._button_press
- `src/ribbonfm/ui/mainwindow.py`: MainWindow.__init__, MainWindow._adopt_widgets, MainWindow._build_children, MainWindow._load_directory, MainWindow._on_dir_loaded, MainWindow._on_dir_error, MainWindow._update_status, MainWindow.on_window_destroy, MainWindow._on_search_changed, MainWindow._on_view_selection_changed, MainWindow._on_drop, MainWindow._toggle_pane, MainWindow._clear_info_pane, MainWindow._update_info_pane, MainWindow._fill_details, MainWindow._on_file_activated, MainWindow._on_ribbon_collapse, MainWindow.handle_action, MainWindow._action_table, MainWindow._options, MainWindow._toggle_nav_pane, MainWindow._toggle_checkboxes, MainWindow._toggle_extensions, MainWindow._apply_pane_visibility, MainWindow._hide_selected, MainWindow._open_terminal_admin, MainWindow._help, MainWindow._pin_to_quick_access, MainWindow._set_sort_mode, MainWindow._show_error, MainWindow._show_info, MainWindow._show_context_menu
- `src/ribbonfm/ui/navigation.py`: NavigationMixin._init_navigation, NavigationMixin.navigate, NavigationMixin._on_navigated_trash, NavigationMixin._canonicalize, NavigationMixin._on_navigated, NavigationMixin.go_back, NavigationMixin.go_forward, NavigationMixin.go_up, NavigationMixin.refresh, NavigationMixin._update_nav_state, NavigationMixin.toggle_show_hidden, NavigationMixin.on_nav_back, NavigationMixin.on_nav_forward, NavigationMixin.on_nav_up, NavigationMixin.on_nav_refresh, NavigationMixin.on_address_activate, NavigationMixin.on_toggle_crumb_edit, NavigationMixin._app_title_text, NavigationMixin.start_location
- `src/ribbonfm/ui/ops.py`: FileOpsMixin._init_clipboard, FileOpsMixin._set_clip, FileOpsMixin.paste, FileOpsMixin._destination_for, FileOpsMixin.new_folder, FileOpsMixin.new_file, FileOpsMixin.rename, FileOpsMixin.delete, FileOpsMixin.delete_permanent, FileOpsMixin._run_for_each, FileOpsMixin.properties, FileOpsMixin.open_selection, FileOpsMixin.open_path, FileOpsMixin._open_trash_item, FileOpsMixin.restore, FileOpsMixin.trash_delete_permanent, FileOpsMixin.empty_trash, FileOpsMixin.open_with_default, FileOpsMixin.open_selection_with, FileOpsMixin.open_with_dialog, FileOpsMixin._pick_program, FileOpsMixin.open_terminal, FileOpsMixin._summarize
- `src/ribbonfm/ui/propsdialog.py`: PropertiesDialog.__init__, PropertiesDialog.run, PropertiesDialog._build_general_tab, PropertiesDialog._build_security_tab, PropertiesDialog._add_perm_matrix, PropertiesDialog._build_perm_editor, PropertiesDialog._build_details_tab, PropertiesDialog._add_grid_row, PropertiesDialog._add_plain_row, PropertiesDialog._type_label, PropertiesDialog._size_label, PropertiesDialog._time
- `src/ribbonfm/ui/ribbon.py`: Ribbon.__init__, Ribbon.build, Ribbon._build_file_backstage, Ribbon._add_menu_item, Ribbon._build_quick_access, Ribbon._build_collapse_toggle, Ribbon._on_collapse_toggled, Ribbon.collapsed, Ribbon.set_checked, Ribbon._apply_check
- `src/ribbonfm/ui/settings.py`: SettingsDialog.__init__, SettingsDialog.run
- `src/ribbonfm/ui/sidepanel.py`: Sidebar.__init__, Sidebar._load_bookmarks, Sidebar._save_bookmarks, Sidebar.refresh, Sidebar._build_devices, Sidebar._places, Sidebar._build_section, Sidebar._on_activated, Sidebar._activate_token, Sidebar._on_mount_done, Sidebar._on_button_press, Sidebar._show_context_menu, Sidebar.add_bookmark, Sidebar.remove_bookmark
- `src/ribbonfm/ui/statusbar.py`: StatusBar.__init__, StatusBar._clear, StatusBar.set
- `tests/test_core.py`: ModeTest.test_rwx_conversion, ModeTest.test_perm_mode_str, ListingTest.setUp, ListingTest.tearDown, ListingTest.test_list_dir_returns_entries, ListingTest.test_show_hidden, ListingTest.test_dir_flags, ListingTest.test_entry_for_path, SortTest.test_dirs_first_key, PermTest.setUp, PermTest.tearDown, PermTest.test_inspect_readable, PermTest.test_is_admin_false_non_root, PathTest.test_home, PathTest.test_free_space_positive, I18nTest.test_zh_cn_resolves, I18nTest.test_locale_discovered

<!-- @@INVENTORY:END@@ -->
