# Architecture

RibbonFM is organised as a layered application so the file-system logic stays
independent of the GTK UI.

```
src/ribbonfm/
├── app.py               Gtk.Application; owns the window, applies CSS
├── config.py            constants, resource/path discovery
├── i18n.py              gettext setup + runtime language switching
├── core/                NON-UI layer (testable, no GTK widgets)
│   ├── pathutils        cross-platform paths, special dirs
│   ├── files            Gio.File operations (list, copy, move, trash...)
│   ├── perm             permission checks + privilege escalation
│   ├── mounts           Gio.VolumeMonitor wrappers
│   ├── sorts            directory-first sort primitives
│   └── tasks            thread pool + GLib.idle_add marshalling
├── ui/                  GTK layer (widgets + controller)
│   ├── mainwindow       thin controller: widgets + action dispatch
│   ├── navigation       history stack + nav/address handlers (mixin)
│   ├── ops              file operations + clipboard + open-with (mixin)
│   ├── ribbon           custom Ribbon toolbar (Stack + StackSwitcher)
│   ├── ribbon_spec      declarative Ribbon tab/group/button layout data
│   ├── addressbar       breadcrumb + editable address entry
│   ├── sidepanel        Places/Bookmarks/Devices tree
│   ├── fileview         TreeView + IconView, sorting & filtering
│   ├── statusbar        selection/count/free-space/permission line
│   ├── menus            item & background context menus
│   ├── dialogs          error/confirm/one-line prompt dialogs
│   └── propsdialog      metadata + permission editor
└── resources/ui|css|locale
```

## Responsibilities

* **`mainwindow.py`** is the single controller. It receives actions from the
  Ribbon, the context menus and the address/sidebar widgets (the same
  `handle_action(action)` entry point), runs the navigation history, and keeps
  the selection/status state.
* **`core/*`** has no GTK imports (except `Gio`/`GLib`), so it is unit-testable
  without a display.

## The Ribbon

GTK3 has no native Ribbon. It is emulated as:

* a `Gtk.Stack` + `Gtk.StackSwitcher` forming the tab strip;
* each tab page a `Gtk.Box` of labelled **groups**;
* each group holding **large buttons** (icon over wrapped label) or **small
  buttons** (icon beside label);
* a toggle button collapses the Stack to a slim tab strip.

The button layout is **data driven** (`ribbon._TABS`), so translators only need
to provide labelled strings and actions are just string keys dispatched by the
controller.

## Threading & responsiveness

Every file operation (`list_dir`, copy, move, trash, delete, mkdir...) is run on
a `ThreadPoolExecutor` (max 4 workers) and the result is marshalled back to the
GTK main loop through `GLib.idle_add` (see `core/tasks.py`). This keeps the UI
responsive on large or slow directories. Icons are resolved once and cached.

## i18n

All user-visible strings are wrapped in `_()`. `i18n.init()` binds the gettext
domain, discovers bundled `.mo` catalogs under `resources/locale/`, and
`set_language()` can switch at runtime (a language change asks the user to
restart so the widget tree can be rebuilt). See `tools/gen_po.py`.
