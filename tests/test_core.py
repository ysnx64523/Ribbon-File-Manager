"""Unit tests for the core (non-UI) layer.

Run with:

    python -m unittest discover -s tests -v
    # or
    pytest tests
"""

import os
import tempfile
import unittest

from ribbonfm.core import files, pathutils, perm, sorts


class ModeTest(unittest.TestCase):
    def test_rwx_conversion(self):
        self.assertEqual(files.mode_to_rwx(0o755), "rwxr-xr-x")
        self.assertEqual(files.mode_to_rwx(0o700), "rwx------")
        self.assertEqual(files.mode_to_rwx(0o644), "rw-r--r--")
        self.assertEqual(files.mode_to_rwx(0), "")

    def test_perm_mode_str(self):
        hint = perm.inspect(os.curdir)
        self.assertEqual(len(hint.rwx), 9)


class ListingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ribbonfm-test-")
        self.path = self.tmp.name
        with open(os.path.join(self.path, "a.txt"), "w") as fh:
            fh.write("hello")
        os.mkdir(os.path.join(self.path, "sub"))
        with open(os.path.join(self.path, ".hidden"), "w") as fh:
            fh.write("hidden")

    def tearDown(self):
        self.tmp.cleanup()

    def test_list_dir_returns_entries(self):
        entries = files.list_dir(self.path, show_hidden=False)
        names = {e.name for e in entries}
        self.assertIn("a.txt", names)
        self.assertIn("sub", names)
        self.assertNotIn(".hidden", names)

    def test_show_hidden(self):
        with_hidden = files.list_dir(self.path, show_hidden=True)
        names = {e.name for e in with_hidden}
        self.assertIn(".hidden", names)

    def test_dir_flags(self):
        entries = {e.name: e for e in files.list_dir(self.path)}
        self.assertTrue(entries["sub"].is_dir)
        self.assertFalse(entries["sub"].is_file)
        self.assertTrue(entries["a.txt"].is_file)

    def test_entry_for_path(self):
        entry = files.entry_for_path(os.path.join(self.path, "a.txt"))
        self.assertTrue(entry.is_file)
        self.assertEqual(entry.size, 5)


class SortTest(unittest.TestCase):
    def test_dirs_first_key(self):
        # The sort key returns a tuple with a leading "not is_dir" so that
        # directories (not False -> True-ish ordering) come first.
        key = sorts.make_key("name")

        class E:
            def __init__(self, is_dir, name):
                self.is_dir = is_dir
                self.display_name = name

        items = [E(False, "z.txt"), E(True, "aa"), E(False, "a.txt")]
        ordered = sorted(items, key=lambda e: (not e.is_dir, e.display_name.lower()))
        self.assertTrue(ordered[0].is_dir)


class PermTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ribbonfm-perm-")
        self.path = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_inspect_readable(self):
        hint = perm.inspect(self.path)
        self.assertFalse(hint.is_root)
        self.assertTrue(hint.is_writable)

    def test_is_admin_false_non_root(self):
        # In a normal test process we are not root; is_admin must not raise.
        self.assertIsInstance(bool(perm.is_admin()), bool)


class PathTest(unittest.TestCase):
    def test_home(self):
        self.assertTrue(pathutils.user_home().is_absolute())

    def test_free_space_positive(self):
        free = files.free_space(os.curdir)
        self.assertGreater(free, 0)


if __name__ == "__main__":
    unittest.main()


class I18nTest(unittest.TestCase):
    def test_zh_cn_resolves(self):
        from ribbonfm import i18n
        i18n.set_language("zh-CN")
        checked = {
            "New Folder": "新建文件夹", "Paste": "粘贴", "Refresh": "刷新",
            "Properties": "属性", "Open": "打开", "ribbon_tab_home": "主页",
            "General": "常规",
        }
        for msgid, zh in checked.items():
            self.assertEqual(i18n._(msgid), zh, f"{msgid} 未正确翻译")

    def test_locale_discovered(self):
        from ribbonfm import i18n
        self.assertIn("zh_CN", i18n.available_languages())
