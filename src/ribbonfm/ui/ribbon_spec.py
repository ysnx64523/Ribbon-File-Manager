"""Data-driven Ribbon layout.

Pure declarative descriptors for the Ribbon tabs, groups and buttons. Keeping
the layout here (separate from the widget construction in ``ribbon.py``) makes it
easy to add tabs/buttons and to localise labels. See :data:`TABS`.

A button action is a ``str`` dispatched by the controller; ``view:``/``sort:``/
``toggle:`` prefixes select the corresponding operation.
"""

from __future__ import annotations


def _btn(id_, key, icon, action, *, large=True, check=False):
    return {"kind": "button", "id": id_, "label_key": key, "icon": icon,
            "action": action, "large": large, "check": check}


def _group(key, buttons, large=False, columns=0):
    return {"kind": "group", "label_key": key, "buttons": buttons,
            "large": large, "columns": columns}


TABS = [
    {
        "id": "file",
        "label_key": "ribbon_tab_file",
        "groups": [
            _group("group_manage", [
                _btn("new_folder", "new_folder", "folder-new", "new_folder"),
                _btn("new_file", "new_file", "text-x-generic", "new_file"),
            ]),
            _group("group_open", [
                _btn("properties", "properties", "document-properties", "properties",
                     large=False),
                _btn("close", "close", "window-close", "close", large=False),
            ]),
        ],
    },
    {
        "id": "home",
        "label_key": "ribbon_tab_home",
        "groups": [
            _group("group_clipboard", [
                _btn("pin", "pin_to_quick_access", "user-bookmarks", "pin_to_quick_access"),
                _btn("cut", "cut", "edit-cut", "cut", large=False),
                _btn("copy", "copy", "edit-copy", "copy", large=False),
                _btn("paste", "paste", "edit-paste", "paste", large=False),
            ], columns=1),
            _group("group_organize", [
                _btn("move_to", "move_to", "folder", "move_to"),
                _btn("copy_to", "copy_to", "edit-copy", "copy_to"),
                _btn("delete", "delete", "user-trash", "delete"),
                _btn("rename", "rename", "edit-rename", "rename"),
            ], large=True),
            _group("group_new", [
                _btn("new_folder", "new_folder", "folder-new", "new_folder"),
                _btn("new_item", "new_item", "document-new", "new_file"),
            ]),
            _group("group_open", [
                _btn("properties", "properties", "document-properties", "properties", large=False),
                _btn("open", "open", "document-open", "open", large=False),
                _btn("edit", "edit", "accessories-text-editor", "edit", large=False),
                _btn("history", "history", "document-open-recent", "history", large=False),
            ]),
            _group("group_select", [
                _btn("select_all", "select_all", "edit-select-all", "select_all", large=False),
                _btn("select_none", "select_none", "edit-clear-all-symbolic", "select_none", large=False),
                _btn("invert", "invert_select", "object-rotate-right", "invert_select", large=False),
            ], columns=1),
            _group("group_filter", [
                _btn("filter", "filter", "view-filter", "filter", large=False),
            ]),
        ],
    },
    {
        "id": "share",
        "label_key": "ribbon_tab_share",
        "groups": [
            _group("group_share", [
                _btn("share", "share", "emblem-shared", "share", large=False),
                _btn("compress", "compress", "package-x-generic", "compress",
                     large=False),
            ]),
            _group("group_system", [
                _btn("open_terminal", "open_terminal", "utilities-terminal",
                     "open_terminal", large=False),
                _btn("mount", "mount", "drive-harddisk", "mount", large=False),
                _btn("unmount", "unmount", "drive-removable-media", "unmount",
                     large=False),
            ]),
        ],
    },
    {
        "id": "view",
        "label_key": "ribbon_tab_view",
        "groups": [
            _group("group_panes", [
                _btn("nav_pane", "nav_pane", "view-restore-symbolic", "toggle:nav_pane", large=False, check=True),
                _btn("preview_pane", "preview_pane", "view-readermode-symbolic", "preview_pane", large=False, check=True),
                _btn("details_pane", "details_pane", "view-list-details-symbolic", "details_pane", large=False, check=True),
            ], columns=1),
            _group("group_layout", [
                _btn("view_huge", "view_huge", "view-grid-symbolic", "view:huge", large=False),
                _btn("view_large", "view_large_icons", "view-grid-symbolic", "view:large", large=False),
                _btn("view_medium", "view_medium", "view-grid-symbolic", "view:medium", large=False),
                _btn("view_small", "view_small_icons", "view-list-symbolic", "view:small", large=False),
                _btn("view_list", "view_list", "view-list-symbolic", "view:list", large=False),
                _btn("view_details", "view_details", "view-list-details-symbolic", "view:details", large=False),
                _btn("view_tiles", "view_tiles", "view-grid-symbolic", "view:tiles", large=False),
                _btn("view_content", "view_content", "view-list-symbolic", "view:content", large=False),
            ], large=False, columns=4),
            _group("group_currentview", [
                _btn("sort_by", "sort_by", "view-sort-ascending", "sort_by", large=False),
                _btn("group_by", "group_by", "view-sort-ascending", "toggle:grouping", large=False, check=True),
                _btn("add_columns", "add_columns", "list-add", "add_columns", large=False),
                _btn("fit_columns", "size_all_columns", "zoom-fit-best", "fit_columns", large=False),
            ], columns=2),
            _group("group_showhide", [
                _btn("checkboxes", "item_checkboxes", "edit-select-all-symbolic", "checkboxes", large=False, check=True),
                _btn("file_ext", "file_extensions", "text-x-generic", "file_extensions", large=False, check=True),
                _btn("hidden_items", "hidden_items", "view-reveal", "toggle:show_hidden", large=False, check=True),
                _btn("hide_selected", "hide_selected", "object-hide", "hide_selected", large=True),
            ], columns=1),
            _group("group_options", [
                _btn("options", "options", "applications-system-symbolic", "options", large=False),
            ]),
        ],
    },
    {
        "id": "manage",
        "label_key": "ribbon_tab_manage",
        "groups": [
            _group("group_system", [
                _btn("open_terminal", "open_terminal", "utilities-terminal",
                     "open_terminal", large=False),
                _btn("mount", "mount", "drive-harddisk", "mount", large=False),
                _btn("unmount", "unmount", "drive-removable-media", "unmount",
                     large=False),
            ]),
        ],
    },
]
