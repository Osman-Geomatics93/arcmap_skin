# -*- coding: utf-8 -*-
"""Shared helpers: translation, icons, widget lookup and the undo log.

Every change the skin makes to QGIS goes through :class:`Changes`, which
records how to take it back. Switching the look off replays the log in
reverse, so QGIS comes back exactly as it was.
"""

import os
import traceback

from qgis.PyQt import sip
from qgis.PyQt.QtCore import QCoreApplication, QSize, Qt
from qgis.PyQt.QtGui import QAction, QIcon
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QFrame,
    QMenu,
    QToolBar,
    QToolButton,
    QWidget,
)

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES = os.path.join(PLUGIN_DIR, "resources")
ICON_DIR = os.path.join(RESOURCES, "icons", "arcmap")
UI_ICON_DIR = os.path.join(RESOURCES, "icons", "ui")

SETTINGS_GROUP = "arcmap_skin"


def tr(text):
    """Translate ``text`` in the ArcMapSkin context."""
    return QCoreApplication.translate("ArcMapSkin", text)


def alive(obj):
    """True when ``obj`` is a live Qt object (not None, not deleted by Qt)."""
    if obj is None:
        return False
    try:
        return not sip.isdeleted(obj)
    except TypeError:
        return True


_ICON_CACHE = {}


def icon_path(name):
    """Absolute path of a hand-drawn ArcMap-style icon (without extension)."""
    return os.path.join(ICON_DIR, name + ".svg")


def arcmap_icon(name):
    """Return a hand-drawn ArcMap-style icon, or an empty QIcon if missing."""
    if name in _ICON_CACHE:
        return _ICON_CACHE[name]
    path = icon_path(name)
    icon = QIcon(path) if os.path.exists(path) else QIcon()
    _ICON_CACHE[name] = icon
    return icon


def ui_icon(name):
    path = os.path.join(UI_ICON_DIR, name + ".svg")
    return QIcon(path) if os.path.exists(path) else QIcon()


def has_icon(name):
    return os.path.exists(icon_path(name))


class Changes:
    """Undo log of everything the skin changed.

    ``set`` reads a property through its getter (``prop()`` or ``isProp()``),
    applies the new value through ``setProp()`` and records a callback that
    puts the old value back. ``add`` records a custom revert callback for
    changes the caller makes directly. ``undo`` runs the callbacks newest
    first; if one fails the rest still run so the interface is never left
    half restored, and the first error is raised at the end.
    """

    def __init__(self):
        self._undo = []

    def __len__(self):
        return len(self._undo)

    @staticmethod
    def _getter(obj, prop):
        if hasattr(obj, prop):
            return getattr(obj, prop)
        is_name = "is" + prop[0].upper() + prop[1:]
        if hasattr(obj, is_name):
            return getattr(obj, is_name)
        raise AttributeError("%r has no getter for %r" % (obj, prop))

    def set(self, obj, prop, value):
        old = self._getter(obj, prop)()
        setter = getattr(obj, "set" + prop[0].upper() + prop[1:])
        setter(value)

        def undo(obj=obj, setter=setter, old=old):
            if alive(obj):
                setter(old)

        self._undo.append(undo)
        return old

    def add(self, undo):
        self._undo.append(undo)

    def undo(self, progress=None):
        error = None
        total = len(self._undo)
        for i, step in enumerate(reversed(self._undo)):
            try:
                step()
            except Exception as exc:  # noqa: BLE001  (keep restoring)
                if error is None:
                    error = exc
                traceback.print_exc()
            if progress is not None:
                progress((i + 1) / total if total else 1.0)
        self._undo = []
        if error is not None:
            raise error


# ---------------------------------------------------------------- lookups


def main_window(iface):
    return iface.mainWindow()


def find_action(win, name):
    """A QGIS QAction by objectName, searched in the whole main window tree."""
    if not name:
        return None
    action = win.findChild(QAction, name)
    if action is not None:
        return action
    # Actions owned by tool buttons or menus that are not direct children
    for child in win.findChildren(QAction):
        if child.objectName() == name:
            return child
    return None


def find_actions(win, names):
    """Actions for ``names`` in order, skipping the ones QGIS lacks."""
    out = []
    for name in names:
        a = find_action(win, name)
        if a is not None:
            out.append(a)
    return out


def find_menu(win, name):
    return win.findChild(QMenu, name)


def find_toolbar(win, name):
    return win.findChild(QToolBar, name)


def find_dock(win, name):
    return win.findChild(QDockWidget, name)


def find_widget(win, cls, name):
    return win.findChild(cls, name)


def top_toolbars(win):
    """Toolbars owned directly by the main window (plugins included)."""
    return [tb for tb in win.findChildren(QToolBar) if tb.parent() is win]


# ---------------------------------------------------------------- widgets


def tool_button(icon=None, tip="", checkable=False, size=16, parent=None):
    btn = QToolButton(parent)
    btn.setAutoRaise(True)
    if icon is not None:
        btn.setIcon(icon)
    btn.setIconSize(QSize(size, size))
    if tip:
        btn.setToolTip(tip)
    btn.setCheckable(checkable)
    btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    return btn


def separator(parent=None, vertical=True):
    line = QFrame(parent)
    line.setObjectName("ArcMapSeparator")
    line.setFrameShape(QFrame.Shape.VLine if vertical else QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Plain)
    return line


def action_text(action):
    """Menu text without accelerator ampersands or trailing ellipsis."""
    text = action.text().replace("&&", "\x00").replace("&", "").replace("\x00", "&")
    return text.rstrip(".").rstrip("…").strip()


def set_restyle(changes, action, icon=None, text=None, tip=None):
    """Swap an action's icon/text/tooltip and record how to undo it."""
    if action is None:
        return
    if icon is not None and not icon.isNull():
        changes.set(action, "icon", icon)
    if text is not None:
        changes.set(action, "text", text)
        changes.set(action, "iconText", text)
    if tip is not None:
        changes.set(action, "toolTip", tip)


def widget_of(action, parent):
    """The QToolButton that shows ``action`` inside ``parent`` (a toolbar)."""
    w = parent.widgetForAction(action) if isinstance(parent, QToolBar) else None
    return w if isinstance(w, QToolButton) else None


def iter_widgets(root):
    yield root
    for w in root.findChildren(QWidget):
        yield w
