"""Paste into the QGIS Python console (or run with exec(open(path).read())).

Prints the objectNames the skin relies on: toolbars with their actions,
top-level menus, dock widgets and status-bar widgets. Use it to check a new
QGIS version before adjusting the specs in menus.py / toolbars.py / panes.py.
"""

from qgis.PyQt.QtWidgets import QDockWidget, QToolBar
from qgis.utils import iface

win = iface.mainWindow()

print("=== TOOLBARS ===")
for tb in win.findChildren(QToolBar):
    if tb.parent() is not win:
        continue
    names = [a.objectName() or ("<sep>" if a.isSeparator() else "<%s>" % a.text()) for a in tb.actions()]
    print("%s (%s): %s" % (tb.objectName(), tb.windowTitle(), ", ".join(names)))

print("\n=== MENUS ===")
bar = win.menuBar()
for act in bar.actions():
    m = act.menu()
    print("%s (%s)" % (m.objectName() if m else "-", act.text()))

print("\n=== DOCKS ===")
for d in win.findChildren(QDockWidget):
    if d.parent() is win:
        print("%s (%s) visible=%s area=%s" % (d.objectName(), d.windowTitle(), d.isVisible(), int(win.dockWidgetArea(d))))

print("\n=== STATUS BAR ===")
for w in win.statusBar().findChildren(object):
    try:
        if w.objectName():
            print("%s: %s" % (w.objectName(), w.metaObject().className()))
    except AttributeError:
        pass
