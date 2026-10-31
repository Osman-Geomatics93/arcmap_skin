# -*- coding: utf-8 -*-
"""Static Qt5/Qt6 compatibility lint over the plugin sources.

The plugin must run on QGIS 3.40 (PyQt5) and QGIS 4 (PyQt6). PyQt6 removed
unscoped enums, ``exec_()``, ``QRegExp`` and the old ``QVariant.Type``
field types, so none of those may appear in the sources.
"""

import glob
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = glob.glob(os.path.join(ROOT, "arcmap_skin", "*.py"))

FORBIDDEN = [
    (r"\bimport PyQt5\b|\bfrom PyQt5\b|\bimport PyQt6\b|\bfrom PyQt6\b", "import Qt through qgis.PyQt"),
    (r"\.exec_\(", "use exec() not exec_()"),
    (r"\bQRegExp\b", "QRegExp is gone in Qt6; use re or QRegularExpression"),
    (r"\bQVariant\.Type\b", "QVariant.Type field types are gone; use QgsField.isNumeric()/typeName()"),
    (r"\bQgsWkbTypes\.GeometryType\b", "use Qgis.GeometryType"),
    (r"\bQgsMapLayerProxyModel\.Filter\b(?!.*fallback)", "use Qgis.LayerFilter (with fallback helper)"),
]

# Enum values that must be scoped (Qt.AlignLeft → Qt.AlignmentFlag.AlignLeft …)
UNSCOPED = re.compile(
    r"\b(Qt|QMessageBox|QDialogButtonBox|QDialog|QFrame|QSizePolicy|QHeaderView|QAbstractItemView|QToolButton|QTabBar)"
    r"\.([A-Z][A-Za-z0-9]+)\b(?!\.)"
)
# Enum *classes* (followed by another member) are fine; these bare names are the known offenders
BARE_OK = {"Qt", "QMessageBox", "QDialogButtonBox"}


class Qt6CompatTest(unittest.TestCase):
    def test_forbidden_patterns(self):
        problems = []
        for path in SOURCES:
            with open(path, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    if "fallback" in line:  # explicitly marked QGIS 3.x fallback
                        continue
                    stripped = line.split("#", 1)[0]
                    for pattern, why in FORBIDDEN:
                        if re.search(pattern, stripped):
                            problems.append("%s:%d: %s" % (os.path.basename(path), lineno, why))
        self.assertEqual(problems, [])

    def test_enums_are_scoped(self):
        problems = []
        for path in SOURCES:
            with open(path, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    stripped = line.split("#", 1)[0]
                    for m in UNSCOPED.finditer(stripped):
                        owner, member = m.group(1), m.group(2)
                        # Qt.AlignmentFlag.X is scoped (member followed by a dot is excluded by the regex);
                        # what remains is a bare member such as Qt.AlignLeft or QMessageBox.Yes.
                        if member in ("StandardButton", "ButtonRole", "DialogCode", "Shape", "Shadow", "Policy",
                                      "ResizeMode", "SelectionBehavior", "SelectionMode", "EditTrigger",
                                      "ToolButtonPopupMode", "ButtonPosition", "Icon"):
                            continue
                        problems.append("%s:%d: %s.%s is an unscoped enum" % (os.path.basename(path), lineno, owner, member))
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
