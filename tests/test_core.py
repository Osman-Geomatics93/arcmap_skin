# -*- coding: utf-8 -*-
"""Unit tests that need no running QGIS GUI.

Run with QGIS's Python so the ``qgis`` package imports::

    "C:/Program Files/QGIS 3.44.6/bin/python-qgis.bat" -m unittest discover -s tests -v
"""

import os
import re
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from arcmap_skin import stylesheet  # noqa: E402
from arcmap_skin.util import Changes, ICON_DIR  # noqa: E402


class Holder:
    def __init__(self):
        self._visible = True
        self._text = "a"

    def isVisible(self):  # noqa: N802
        return self._visible

    def setVisible(self, v):  # noqa: N802
        self._visible = v

    def text(self):
        return self._text

    def setText(self, t):  # noqa: N802
        self._text = t


class ChangesTest(unittest.TestCase):
    def test_set_and_undo_restores_in_reverse(self):
        h = Holder()
        c = Changes()
        c.set(h, "visible", False)
        c.set(h, "text", "b")
        c.set(h, "text", "c")
        self.assertFalse(h.isVisible())
        self.assertEqual(h.text(), "c")
        c.undo()
        self.assertTrue(h.isVisible())
        self.assertEqual(h.text(), "a")
        self.assertEqual(len(c), 0)

    def test_undo_continues_after_failure_and_raises_first(self):
        order = []
        c = Changes()
        c.add(lambda: order.append(1))

        def boom():
            order.append(2)
            raise ValueError("boom")

        c.add(boom)
        c.add(lambda: order.append(3))
        with self.assertRaises(ValueError):
            c.undo()
        self.assertEqual(order, [3, 2, 1])

    def test_progress_reports_fraction(self):
        seen = []
        c = Changes()
        for _ in range(4):
            c.add(lambda: None)
        c.undo(seen.append)
        self.assertEqual(seen[-1], 1.0)
        self.assertEqual(len(seen), 4)


class StyleSheetTest(unittest.TestCase):
    def test_block_round_trip(self):
        sheet = "QWidget { color: red; }\n"
        with_block = stylesheet.insert_block(sheet, "QToolBar { }")
        self.assertTrue(with_block.startswith(stylesheet.BEGIN))
        self.assertTrue(stylesheet.has_block(with_block))
        self.assertTrue(with_block.endswith(sheet))
        self.assertEqual(stylesheet.remove_block(with_block), sheet)

    def test_insert_replaces_existing_block(self):
        once = stylesheet.insert_block("", "a {}")
        twice = stylesheet.insert_block(once, "b {}")
        self.assertEqual(twice.count(stylesheet.BEGIN), 1)
        self.assertIn("b {}", twice)
        self.assertNotIn("a {}", twice)

    def test_variables_resolve(self):
        variables = stylesheet.load_variables("@text: #111;\n@bg-panel: #fff;\n")
        self.assertEqual(variables, {"text": "#111", "bg-panel": "#fff"})
        out = stylesheet.substitute("a { color: @text; background: @bg-panel; x: @unknown; }", variables)
        self.assertEqual(out, "a { color: #111; background: #fff; x: @unknown; }")

    def test_palette_follows_theme(self):
        from qgis.PyQt.QtGui import QPalette

        for theme in ("arcmap_light", "arcmap_dark"):
            palette = stylesheet.palette_for(theme)
            variables = stylesheet.theme_variables(theme)
            self.assertEqual(palette.color(QPalette.ColorRole.Window).name(), variables["bg-window"])
            self.assertEqual(palette.color(QPalette.ColorRole.Text).name(), variables["text"])
        dark = stylesheet.palette_for("arcmap_dark").color(QPalette.ColorRole.Window)
        self.assertLess(dark.lightness(), 100)

    def test_theme_has_no_unresolved_tokens(self):
        for theme in ("arcmap_light", "arcmap_dark"):
            qss = stylesheet.load_qss(theme)
            self.assertGreater(len(qss), 2000)
            self.assertEqual(sorted(set(re.findall(r"@[a-z][a-z-]+", qss))), [], theme)
            # every referenced ui icon exists
            for path in re.findall(r"url\(([^)]+)\)", qss):
                self.assertTrue(os.path.exists(path), path)


class SpecTest(unittest.TestCase):
    def test_every_referenced_icon_exists(self):
        from arcmap_skin import contents_views, icon_theme, menus, toolbars

        names = set(icon for _, icon in menus.ALIASES.values() if icon)
        names |= set(icon_theme.ARCMAP_AS_QGIS)
        names |= {icon for _, _, icon in contents_views.VIEWS}
        from arcmap_skin import attribute_table

        names |= {e[1] for e in attribute_table.TOOLBAR if e and e[1]}
        names |= {e[1] for e in attribute_table.TABLE_OPTIONS if e and e[1]}
        for _, _, items in toolbars.TOOLBARS:
            for item in items:
                if isinstance(item, tuple) and item[0] in ("dock", "toolbar"):
                    names.add(item[3])
        # every arcmap_icon("…") literal in any module
        import glob

        for path in glob.glob(os.path.join(ROOT, "arcmap_skin", "*.py")):
            with open(path, encoding="utf-8") as fh:
                names |= set(re.findall(r'arcmap_icon\("([a-z0-9_]+)"\)', fh.read()))
        missing = sorted(n for n in names if not os.path.exists(os.path.join(ICON_DIR, n + ".svg")))
        self.assertEqual(missing, [])

    def test_toolbar_specs_well_formed(self):
        from arcmap_skin import toolbars

        seen = set()
        for object_name, title, items in toolbars.TOOLBARS:
            self.assertTrue(object_name.startswith("ArcMap"))
            self.assertNotIn(object_name, seen)
            seen.add(object_name)
            self.assertTrue(items)

    def test_menu_specs_well_formed(self):
        from arcmap_skin import menus

        kinds = {"sep", "alias", "custom", "menu", "sub", "dock", "toolbars", "qgis_menus", "docks", "bookmarks", "basemaps"}

        def walk(items):
            for item in items:
                if isinstance(item, str):
                    continue
                self.assertIn(item[0], kinds)
                if item[0] == "sub":
                    walk(item[3])

        for _, _, items in menus.MENUS:
            walk(items)

    def test_color_ramps_json_valid(self):
        import json

        from arcmap_skin.util import RESOURCES

        with open(os.path.join(RESOURCES, "color_ramps.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertGreaterEqual(len(data), 30)
        for entry in data:
            self.assertIn("name", entry)
            self.assertTrue("stops" in entry or "colors" in entry)
            if "stops" in entry:
                offsets = [o for o, _ in entry["stops"]]
                self.assertEqual(offsets, sorted(offsets))
                self.assertEqual(offsets[0], 0)
                self.assertEqual(offsets[-1], 1)


class ToolboxTest(unittest.TestCase):
    def test_toolbox_spec_shape(self):
        from arcmap_skin import arctoolbox

        seen = set()
        for toolbox, toolsets in arctoolbox.TOOLBOXES:
            self.assertNotIn(toolbox, seen)
            seen.add(toolbox)
            for toolset, tools in toolsets:
                self.assertTrue(tools, (toolbox, toolset))
                for name, candidates in tools:
                    self.assertTrue(candidates, name)
                    for c in candidates:
                        self.assertRegex(c, r"^[a-z0-9]+:[A-Za-z0-9_.]+$")


class DmsTest(unittest.TestCase):
    def test_dms_and_ddm(self):
        from arcmap_skin.mapview import _ddm, _dms

        self.assertEqual(_dms(31.5, "EW"), "31°30'00.00\"E")
        self.assertEqual(_dms(-0.5, "NS"), "0°30'00.00\"S")
        self.assertEqual(_ddm(31.25, "EW"), "31°15.0000'E")


class QmWriterTest(unittest.TestCase):
    def test_qm_round_trip(self):
        import tempfile

        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import i18n
        from qgis.PyQt.QtCore import QCoreApplication, QTranslator

        global _APP
        _APP = QCoreApplication.instance() or QCoreApplication([])  # keep alive
        path = os.path.join(tempfile.mkdtemp(), "t.qm")
        n = i18n.write_qm(path, {"Hello": "Marhaba", "Table Of Contents": "TOC", "Skip": ""})
        self.assertEqual(n, 2)
        t = QTranslator()
        self.assertTrue(t.load(path))
        QCoreApplication.installTranslator(t)
        try:
            self.assertEqual(QCoreApplication.translate("ArcMapSkin", "Hello"), "Marhaba")
            self.assertEqual(QCoreApplication.translate("ArcMapSkin", "Table Of Contents"), "TOC")
            self.assertEqual(QCoreApplication.translate("ArcMapSkin", "Skip"), "Skip")
            self.assertEqual(QCoreApplication.translate("Other", "Hello"), "Hello")
        finally:
            QCoreApplication.removeTranslator(t)

    def test_arabic_json_covers_all_strings(self):
        import json

        with open(os.path.join(ROOT, "arcmap_skin", "i18n", "arcmap_skin_ar.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertGreater(len(data), 500)
        for source, target in data.items():
            # placeholders must survive translation
            for token in ("%d", "%s"):
                self.assertEqual(source.count(token), target.count(token), source)


class MetadataTest(unittest.TestCase):
    def test_metadata(self):
        with open(os.path.join(ROOT, "arcmap_skin", "metadata.txt"), encoding="utf-8") as fh:
            text = fh.read()
        for key in ("name=", "qgisMinimumVersion=", "version=", "description=", "author=", "email=", "supportsQt6=True"):
            self.assertIn(key, text)


if __name__ == "__main__":
    unittest.main()


_APP = None

