# -*- coding: utf-8 -*-
"""The skin's style sheet block.

The block is wrapped in begin/end markers and inserted at the *front* of the
application style sheet, so rules from QGIS itself and from other plugins,
which come later, still win where they are more specific. Removing the
look removes only the block.

:class:`StyleSheetBlock` also watches the main window for ``StyleChange``
events. QGIS rewrites the application style sheet when the user changes
UI options; if the block is lost, it is put back on the next event-loop
turn (one zero-delay timer coalesces several changes).
"""

import os
import re

from qgis.PyQt.QtCore import QEvent, QObject, QTimer
from qgis.PyQt.QtWidgets import QApplication

from .util import RESOURCES, UI_ICON_DIR, alive

BEGIN = "/* ArcMapSkin:begin */"
END = "/* ArcMapSkin:end */"
THEMES_DIR = os.path.join(RESOURCES, "themes")

_VAR_DEF = re.compile(r"^\s*@([A-Za-z0-9_-]+)\s*:\s*(.+?)\s*;\s*$", re.MULTILINE)
_VAR_USE = re.compile(r"@([A-Za-z0-9_-]+)")


def _qss_path(path):
    # QSS url() wants forward slashes, even on Windows.
    return path.replace("\\", "/")


def load_variables(text):
    """Parse ``@name: value;`` lines into a dict."""
    return {m.group(1): m.group(2) for m in _VAR_DEF.finditer(text)}


def substitute(qss, variables):
    """Replace ``@name`` tokens with their values. Unknown names are kept."""

    def repl(m):
        return variables.get(m.group(1), m.group(0))

    return _VAR_USE.sub(repl, qss)


def load_qss(theme="arcmap_light", extra_variables=None):
    """Return the theme's stylesheet text with variables and @icons resolved."""
    folder = os.path.join(THEMES_DIR, theme)
    with open(os.path.join(folder, "variables.qss"), encoding="utf-8") as fh:
        variables = load_variables(fh.read())
    style_path = os.path.join(folder, "style.qss")
    if not os.path.exists(style_path):  # dark theme shares the light rules
        style_path = os.path.join(THEMES_DIR, "arcmap_light", "style.qss")
    with open(style_path, encoding="utf-8") as fh:
        style = fh.read()
    icon_dir = UI_ICON_DIR + ("_dark" if theme.endswith("dark") and os.path.isdir(UI_ICON_DIR + "_dark") else "")
    variables["icons"] = _qss_path(icon_dir)
    if extra_variables:
        variables.update(extra_variables)
    return substitute(style, variables)


def wrap(block):
    return "%s\n%s\n%s\n" % (BEGIN, block.strip("\n"), END)


def has_block(sheet):
    return BEGIN in sheet and END in sheet


def remove_block(sheet):
    """``sheet`` without the marked block (and without a trailing blank line)."""
    start = sheet.find(BEGIN)
    if start < 0:
        return sheet
    end = sheet.find(END, start)
    if end < 0:
        return sheet
    end += len(END)
    if end < len(sheet) and sheet[end] == "\n":
        end += 1
    return sheet[:start] + sheet[end:]


def insert_block(sheet, block):
    """``sheet`` with the block at the front, replacing an existing one."""
    return wrap(block) + remove_block(sheet)


class StyleSheetBlock(QObject):
    """Applies the block on creation and keeps it in place until ``remove``."""

    def __init__(self, win, block):
        super().__init__(win)
        self._win = win
        self._block = block
        self._armed = False
        self._active = True
        self.apply()
        win.installEventFilter(self)

    def apply(self):
        app = QApplication.instance()
        app.setStyleSheet(insert_block(app.styleSheet(), self._block))

    def eventFilter(self, obj, event):  # noqa: N802
        if self._active and event.type() == QEvent.Type.StyleChange and not self._armed:
            self._armed = True
            QTimer.singleShot(0, self._resync)
        return False

    def _resync(self):
        self._armed = False
        if not self._active:
            return
        app = QApplication.instance()
        if app is not None and not has_block(app.styleSheet()):
            self.apply()

    def remove(self):
        self._active = False
        if alive(self._win):
            self._win.removeEventFilter(self)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(remove_block(app.styleSheet()))
