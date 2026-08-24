#!/usr/bin/env python3
"""Generate ``po/*.po`` files and compile ``.mo`` into the bundled ``locale``.

Usage::

    python tools/gen_po.py            # read po/ribbonfm.pot, emit zh_CN.po
    make -C po compile                # msgfmt into resources/locale/<lang>/LC_MESSAGES

This script is a simple maintainer helper. It merges the current translation
dictionary with the extracted template, leaving untranslated entries empty so
the running app falls back to the English msgids.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POT = ROOT / "po" / "ribbonfm.pot"

# language -> {msgid: msgstr}
TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh_CN": {
        # Ribbon tabs / groups
        "ribbon_tab_file": "文件",
        "ribbon_tab_home": "主页",
        "ribbon_tab_share": "共享",
        "ribbon_tab_view": "查看",
        "ribbon_tab_manage": "管理",
        "ribbon_collapse": "折叠功能区",
        "group_new": "新建",
        "group_manage": "管理",
        "group_open": "打开",
        "group_clipboard": "剪贴板",
        "group_organize": "组织",
        "group_actions": "操作",
        "group_view": "视图",
        "group_sort": "排序",
        "group_filter": "筛选",
        "group_system": "系统",
        "group_share": "共享",
        "group_select": "选择",
        "group_filter": "筛选器",
        "group_panes": "窗格",
        "group_layout": "布局",
        "group_currentview": "当前视图",
        "group_showhide": "显示/隐藏",
        "group_options": "选项",
        "nav_pane": "导航窗格",
        "preview_pane": "预览窗格",
        "details_pane": "详细信息窗格",
        "view_huge": "超大图标",
        "view_large": "大图标",
        "view_medium": "中图标",
        "view_small": "小图标",
        "view_list": "列表",
        "view_details": "详细信息",
        "view_tiles": "平铺",
        "view_content": "内容",
        "sort_by": "排序方式",
        "group_by": "分组依据",
        "add_columns": "添加列",
        "size_all_columns": "把所有列调整为合适的大小",
        "item_checkboxes": "项目复选框",
        "file_extensions": "文件扩展名",
        "hidden_items": "隐藏的项目",
        "hidden": "隐藏",
        "selected_items": "所选项目",
        "hide_selected": "隐藏所选项目",
        # Ribbon buttons
        "pin_to_quick_access": "固定到快速访问",
        "move_to": "移动到",
        "copy_to": "复制到",
        "new_item": "新建",
        "open": "打开",
        "edit": "编辑",
        "history": "历史记录",
        "select_none": "全部取消",
        "filter": "筛选器",
        "new_folder": "新建文件夹",
        "new_file": "新建文件",
        "close": "退出",
        "cut": "剪切",
        "copy": "复制",
        "paste": "粘贴",
        "delete": "删除",
        "rename": "重命名",
        "properties": "属性",
        "select_all": "全选",
        "invert_select": "反向选择",
        "refresh": "刷新",
        "view_large_icons": "大图标",
        "view_small_icons": "小图标",
        "view_list": "列表",
        "view_details": "详细信息",
        "sort_by_name": "按名称",
        "sort_by_size": "按大小",
        "sort_by_type": "按类型",
        "sort_by_mtime": "按修改时间",
        "show_hidden": "显示隐藏文件",
        "group_by_type": "按类型分组",
        "open_terminal": "打开终端",
        "Open Terminal": "打开终端",
        "No supported terminal was found on the system.": "系统上未找到受支持的终端程序。",
        "open_terminal_admin": "以管理员身份打开终端",
        "options": "选项",
        "help": "帮助",
        "close": "退出",
        "Administrator terminal": "管理员终端",
        "Options": "选项",
        "Options are not yet available.": "选项功能暂不可用。",
        "A cross-platform Ribbon-style file manager.": "一款跨平台的 Ribbon 风格文件管理器。",
        "mount": "挂载",
        "unmount": "卸载",
        "share": "共享",
        "compress": "压缩",
        # Menus
        "Open": "打开",
        "Open With": "打开方式",
        "Choose an application to open {name}": "选择用于打开 {name} 的应用程序",
        "Search programs": "搜索程序",
        "Browse a custom program...": "浏览自定义程序...",
        "Choose a program": "选择程序",
        "Executables": "可执行文件",
        "No matching application": "没有匹配的应用程序",
        "Cancel": "取消",
        "Open With...": "打开方式...",
        "Cut": "剪切",
        "Copy": "复制",
        "Rename...": "重命名...",
        "Move to Trash": "移到回收站",
        "Delete Permanently": "永久删除",
        "New Folder": "新建文件夹",
        "New File": "新建文件",
        "Select All": "全选",
        # Sidebar
        "Places": "位置",
        "Bookmarks": "书签",
        "Devices": "设备",
        "Not mounted": "未挂载",
        "Could not mount device": "无法挂载设备",
        "Network": "网络",
        "Network locations": "网络位置",
        "File system": "文件系统",
        "Home": "主目录",
        "Desktop": "桌面",
        "Documents": "文档",
        "Downloads": "下载",
        "Pictures": "图片",
        "Music": "音乐",
        "Videos": "视频",
        "Add to bookmarks": "添加到书签",
        "Remove bookmark": "移除书签",
        # Status bar
        "Location: {loc}": "位置：{loc}",
        "{n} items": "{n} 个项目",
        "{n} selected": "已选择 {n} 项",
        "Free space: {size}": "可用空间：{size}",
        "User: {user}": "用户：{user}",
        "administrator": "管理员",
        "Read only": "只读",
        # Dialogs / errors
        "Cannot open folder": "无法打开文件夹",
        "Move {n} item(s) to Trash?": "将 {n} 个项目移到回收站？",
        "Permanently delete {n} item(s)?": "永久删除 {n} 个项目？",
        "This cannot be undone.": "此操作无法撤销。",
        "Some items were not pasted": "部分项目未粘贴",
        "Some items could not be moved to Trash": "部分项目无法移到回收站",
        "Some items could not be deleted": "部分项目无法删除",
        "Rename": "重命名",
        "Rename failed": "重命名失败",
        "New name:": "新名称：",
        "Folder name:": "文件夹名称：",
        "File name:": "文件名：",
        "Could not create folder": "无法创建文件夹",
        "Could not create file": "无法创建文件",
        "No application found": "未找到应用程序",
        "There is no registered application for this type.": "此类型没有注册的应用程序。",
        "Could not open this file": "无法打开此文件",
        "Could not open terminal": "无法打开终端",
        "Not implemented yet": "尚未实现",
        # Properties dialog
        "Properties": "属性",
        "General": "常规",
        "Security": "安全",
        "Details": "详细信息",
        "Object name": "对象名称",
        "Owner": "所有者",
        "Group": "组",
        "Read": "读取",
        "Write": "写入",
        "Execute": "执行",
        "Others": "其他",
        "File type": "文件类型",
        "Size on disk": "占用空间",
        "Created": "创建时间",
        "Accessed": "访问时间",
        "Read-only": "只读",
        "Hidden": "隐藏",
        "Octal mode": "八进制模式",
        "Edit": "编辑",
        "Path": "路径",
        "Permissions are not available.": "无法获取权限信息。",
        "This location is writable by all users or is managed with "
        "elevated privileges.": "此位置对所有用户可写，或由提权管理。",
        "Name": "名称",
        "Type": "类型",
        "Location": "位置",
        "Size": "大小",
        "Modified": "修改时间",
        "Permissions": "权限",
        "Owner": "所有者",
        "Group": "组",
        "Change permissions": "修改权限",
        "Octal mode, e.g. 755": "八进制模式，如 755",
        "Invalid octal mode": "无效的八进制模式",
        "Use a value such as 755.": "请使用类似 755 的值。",
        "Permissions updated.": "权限已更新。",
        "This location is writable by all users or is managed with "
        "elevated privileges.": "此位置对所有用户可写，或由提权管理。",
        "Folder": "文件夹",
        "File": "文件",
        "Drive": "驱动器",
        "Symbolic link": "符号链接",
        "Symbolic link to {target}": "指向 {target} 的符号链接",
        # Language switch
        "Language changed": "语言已更改",
        "Please restart the application for the change to take effect.":
            "请重启应用程序以使更改生效。",
        # Remaining visible strings found by the i18n audit
        "(folder)": "（文件夹）",
        "Paste": "粘贴",
        "Refresh": "刷新",
        "Trash": "回收站",
        "Restore": "还原",
        "Empty Trash": "清空回收站",
        "Not available in Trash": "回收站中不可用",
        "This action is not available for items in the Trash.":
            "回收站中的项目不支持此操作。",
        "This file is in the Trash. Restore it to open it.":
            "此文件已在回收站中，请先还原再打开。",
        "Some items could not be restored": "部分项目无法还原",
        "Empty the Trash?": "清空回收站？",
        "All items in the Trash will be permanently deleted.":
            "回收站中的所有项目将被永久删除。",
        "Trash emptied.": "回收站已清空。",
        "Pasted {n} item(s)": "已粘贴 {n} 个项目",
        "Some items could not be dropped": "部分项目无法放入",
        "Symbolic link to {t}": "指向 {t} 的符号链接",
        "New File.txt": "新建文件.txt",
        "Could not change permissions: {err}": "无法更改权限：{err}",
        "Failed to start the privileged helper: {err}": "无法启动提权助手：{err}",
        "Privilege escalation is not supported on this platform.":
            "此平台不支持权限提升。",
        "The '{action}' action is a placeholder.": "“{action}”操作仅为占位符。",
        "The folder could not be read. {err}": "无法读取该文件夹。{err}",
        "The privileged operation timed out.": "提权操作超时。",
        "The privileged operation was rejected: {msg}": "提权操作被拒绝：{msg}",
        "This location is not a readable directory: {path}":
            "此位置不是可读目录：{path}",
        "This would open a terminal with elevated privileges.":
            "这将以提权身份打开终端。",
        "You cancelled the authentication request.": "您取消了身份验证请求。",
        "osascript escalation is not wired up in this build.":
            "此构建未接入 osascript 提权。",
        "pkexec is not available to elevate privileges.": "系统没有 pkexec，无法提权。",
        "runas escalation is not wired up in this build.": "此构建未接入 runas 提权。",
    },
}


def _concat_msgid(msgid: str, line: str) -> str:
    # xgettext emits multi-line msgid fragments as separate quoted lines.
    return msgid.rstrip("\n") + line.rstrip("\n")


def _project_version() -> str:
    """Read the version from pyproject.toml so the .po header stays in sync."""
    import re
    m = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text("utf-8"), re.M)
    return m.group(1) if m else "0.1.0"


def generate(lang: str, translations: dict[str, str]) -> str:
    entries: list[str] = []
    entries.append('msgid ""')
    entries.append('msgstr ""')
    entries.append('"Project-Id-Version: ribbonfm %s\\n"' % _project_version())
    entries.append('"MIME-Version: 1.0\\n"')
    entries.append('"Content-Type: text/plain; charset=UTF-8\\n"')
    entries.append('"Content-Transfer-Encoding: 8bit\\n"')
    entries.append('"Language: %s\\n"' % lang)
    entries.append("")
    entries.append("")

    current_id: list[str] = []
    records: dict[str, str] = {}
    with open(POT, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("msgid "):
                current_id = [_parse_quoted(line[6:])]
            elif line.startswith('"') and current_id:
                current_id.append(line.strip('"'))
            elif line.strip() == "":
                if current_id:
                    records["".join(current_id)] = ""
                    current_id = []
    if current_id:
        records["".join(current_id)] = ""

    # Also carry translation keys that xgettext cannot extract (dynamic keys),
    # so ribbon label keys for example are localised too.
    for msgid in translations:
        records.setdefault(msgid, "")

    for msgid in records:
        msgid = msgid.rstrip("\n")
        msgstr = translations.get(msgid, "")
        entries.append('msgid %s' % _escape(msgid))
        entries.append('msgstr %s' % _escape(msgstr))
        entries.append("")
    return "\n".join(entries) + "\n"


def _parse_quoted(s: str) -> str:
    # strip surrounding quotes and unescape \n etc minimally
    s = s.strip()
    if not s.startswith('"'):
        return s
    out = s[1:]
    if out.endswith('"'):
        out = out[:-1]
    return out


def _escape(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace(
        "\n", "\\n") + '"'


def compile_mo(po_path: Path) -> Path:
    lang = po_path.stem
    out = ROOT / "src" / "ribbonfm" / "resources" / "locale" / lang / "LC_MESSAGES"
    out.mkdir(parents=True, exist_ok=True)
    mo = out / "ribbonfm.mo"
    subprocess.run(["msgfmt", "-o", str(mo), str(po_path)], check=True)
    return mo


def _ensure_pot() -> None:
    """Generate the template from sources if it is missing (e.g. in CI).

    Falls back silently: the translation dict still provides the curated keys,
    and any source strings not in the POT simply fall back to English.
    """
    if POT.exists():
        return
    try:
        import subprocess
        files = [str(p) for p in sorted(ROOT.joinpath("src").rglob("*.py"))]
        subprocess.run(
            ["xgettext", "-L", "Python", "--keyword=_", "--keyword=_:1",
             "-d", "ribbonfm", "-o", str(POT), *files],
            check=True, capture_output=True, text=True)
    except Exception:
        # POT is optional; generation continues with the translation dict.
        POT.parent.mkdir(parents=True, exist_ok=True)
        if not POT.exists():
            POT.write_text('msgid ""\nmsgstr ""\n', encoding="utf-8")


def main() -> int:
    _ensure_pot()
    for lang, translations in TRANSLATIONS.items():
        po = ROOT / "po" / f"{lang}.po"
        po.write_text(generate(lang, translations), encoding="utf-8")
        mo = compile_mo(po)
        print(f"wrote {po} and {mo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
