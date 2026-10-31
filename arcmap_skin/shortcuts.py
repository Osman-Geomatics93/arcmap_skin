# -*- coding: utf-8 -*-
"""ArcMap keyboard habits: Z = Zoom In tool, X = Zoom Out tool, C = Pan,
E = Edit Tool (move), S = Select Features. Applied through the QGIS
shortcuts manager and restored on undo.
"""

from qgis.gui import QgsGui
from qgis.PyQt.QtGui import QKeySequence

from .util import alive, find_action

SHORTCUTS = [
    ("mActionZoomIn", "Z"),
    ("mActionZoomOut", "X"),
    ("mActionPan", "C"),
    ("mActionSelectFeatures", "S"),
    ("mActionIdentify", "I"),
]


def apply_shortcuts(iface, changes):
    win = iface.mainWindow()
    manager = QgsGui.shortcutsManager()
    applied = []
    for name, key in SHORTCUTS:
        action = find_action(win, name)
        if action is None:
            continue
        # Do not steal a key another action already uses.
        if manager.objectForSequence(QKeySequence(key)) is not None:
            continue
        previous = action.shortcut().toString()
        if manager.setObjectKeySequence(action, key):
            applied.append((action, previous))

    def undo(applied=applied, manager=manager):
        for action, previous in applied:
            if alive(action):
                manager.setObjectKeySequence(action, previous)

    changes.add(undo)
    return applied
