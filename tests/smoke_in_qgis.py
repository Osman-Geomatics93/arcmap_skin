"""Smoke test: run from the QGIS Python console with the plugin installed.

    exec(open(r"D:/QGIS_Plugins/Arcmap_Skin/tests/smoke_in_qgis.py").read())

Switches the look off, checks QGIS is back to normal, switches it on, and
checks the ArcMap pieces are in place and every core toolbar action is
reachable from an ArcMap toolbar or menu. Prints PASS or FAIL + reasons.
"""

from qgis.PyQt.QtWidgets import QApplication, QDockWidget, QMenu, QToolBar
from qgis.utils import iface, plugins

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


plugin = plugins.get("arcmap_skin")
check(plugin is not None, "plugin 'arcmap_skin' not loaded")
win = iface.mainWindow()

if plugin is not None:
    from arcmap_skin import stylesheet, toolbars

    # ---- off
    if plugin.on:
        plugin.disable()
    for _ in range(20):
        QApplication.processEvents()
    check(not stylesheet.has_block(QApplication.instance().styleSheet()), "stylesheet block still present when off")
    check(win.statusBar().isVisible(), "status bar hidden when off")
    check(not [tb for tb in win.findChildren(QToolBar) if tb.objectName().startswith("ArcMap")], "ArcMap toolbars remain when off")
    # "ArcMapSkin" is the Plugins ▸ ArcMap Skin menu QGIS itself creates for the toggle action.
    leftover_menus = [m.objectName() for m in win.findChildren(QMenu)
                      if m.objectName().startswith("ArcMap") and m.objectName() != "ArcMapSkin"]
    check(not leftover_menus, "ArcMap menus remain when off: %s" % leftover_menus)
    check(win.menuBar().actions() and any(a.menu() and a.menu().objectName() == "mProjectMenu" for a in win.menuBar().actions()),
          "QGIS Project menu not back on the menu bar when off")
    check(win.findChild(QDockWidget, "Layers").windowTitle() != "Table Of Contents", "Layers dock still titled Table Of Contents when off")

    # ---- on
    plugin.enable()
    for _ in range(20):
        QApplication.processEvents()
    check(plugin.on, "enable() did not switch on")
    check(stylesheet.has_block(QApplication.instance().styleSheet()), "stylesheet block missing when on")
    check(not win.statusBar().isVisible(), "QGIS status bar visible when on")
    from qgis.PyQt.QtGui import QKeySequence
    from qgis.gui import QgsGui
    z = QgsGui.shortcutsManager().objectForSequence(QKeySequence("Z"))
    check(z is not None and z.objectName() == "mActionZoomIn", "Z shortcut not bound to Zoom In")
    for name in ("ArcMapStandardToolBar", "ArcMapToolsToolBar", "ArcMapEditorToolBar"):
        check(win.findChild(QToolBar, name) is not None, "missing toolbar %s" % name)
    for name in ("ArcMapFileMenu", "ArcMapEditMenu", "ArcMapViewMenu", "ArcMapSelectionMenu", "ArcMapGeoprocessingMenu",
                 "ArcMapCustomizeMenu", "ArcMapWindowsMenu", "ArcMapHelpMenu"):
        check(win.findChild(QMenu, name) is not None, "missing menu %s" % name)
    check(win.findChild(QDockWidget, "Layers").windowTitle() == "Table Of Contents", "Layers dock not titled Table Of Contents")
    check(win.findChild(QDockWidget, "ArcMapToolboxDock") is not None, "ArcToolbox dock missing")
    check(win.findChild(QDockWidget, "ArcMapCreateFeaturesDock") is not None, "Create Features dock missing")
    check(win.findChild(QToolBar, "ArcMapSnappingToolBar") is not None, "ArcMap Snapping toolbar missing")
    check(win.findChild(QToolBar, "ArcMapDrawToolBar") is not None, "Draw toolbar missing")
    check(win.findChild(QToolBar, "ArcMapLabelingToolBar") is not None, "Labeling toolbar missing")
    check(win.findChild(QDockWidget, "ArcMapAttributesDock") is not None, "Attributes dock missing")
    check(win.findChild(QDockWidget, "ArcMapLabelManagerDock") is not None, "Label Manager dock missing")
    from qgis.PyQt.QtWidgets import QProgressBar
    check(win.centralWidget().findChild(QProgressBar, "ArcMapTaskProgress") is not None, "task progress bar missing")
    tbx = win.findChild(QDockWidget, "ArcMapToolboxDock")
    if tbx is not None:
        from qgis.PyQt.QtWidgets import QTreeWidget
        tree = tbx.findChild(QTreeWidget, "ArcMapToolboxTree")
        n = 0
        if tree is not None:
            for i in range(tree.topLevelItemCount()):
                tb_item = tree.topLevelItem(i)
                for j in range(tb_item.childCount()):
                    n += tb_item.child(j).childCount()
        check(n >= 80, "ArcToolbox has only %d tools" % n)
    for key in ("add_data", "find", "select_by_attributes", "start_editing", "stop_editing", "arctoolbox_dock",
                "create_features_dock", "reset_layout", "getting_started", "connect_folder", "edit_tool",
                "attributes_dock", "label_manager", "pause_labeling", "magnifier", "measure_window", "customize"):
        check(key in plugin.actions, "custom action %s missing" % key)
    check(win.findChild(QToolBar, "mFileToolBar") is None or not win.findChild(QToolBar, "mFileToolBar").isVisible(),
          "QGIS Project toolbar still visible")
    check(win.centralWidget().findChild(QToolBar.__mro__[1].__mro__[0], "ArcMapStatusBar") is not None or
          win.findChild(type(win.centralWidget()), "ArcMapStatusBar") is not None, "ArcMap status bar missing")

    # ---- coverage: every action of the replaced QGIS toolbars is reachable
    reachable = set()

    def collect(widget):
        for a in widget.actions():
            reachable.add(a)
            if a.menu() is not None:
                collect(a.menu())
        for btn in widget.findChildren(type(widget)) if False else []:
            pass

    for tb in win.findChildren(QToolBar):
        if tb.objectName().startswith("ArcMap"):
            collect(tb)
            for child in tb.children():
                if hasattr(child, "menu") and callable(child.menu) and child.menu() is not None:
                    collect(child.menu())
                if hasattr(child, "defaultAction") and child.defaultAction() is not None:
                    reachable.add(child.defaultAction())
    for m in win.findChildren(QMenu):
        if m.objectName().startswith("ArcMap"):
            collect(m)
    later = {"mActionStyleManager", "mActionNewMeshLayer", "mActionNewVirtualLayer", "mActionNewSpatiaLiteLayer",
             "mActionNewGeoPackageLayer", "mActionNewVectorLayer", "mActionNewMemoryLayer", "mActionAddSpatiaLiteLayer",
             "mActionAddVirtualLayer", "mActionAddStacLayer", "mActionAddWcsLayer", "mActionHelpContents", "mActionAllEdits"}
    from qgis.PyQt.QtWidgets import QWidgetAction

    def covered(tb, a):
        if a in reachable:
            return True
        if isinstance(a, QWidgetAction):
            # a QGIS tool button with a menu: reachable if any of its tools is
            w = tb.widgetForAction(a)
            inner = []
            if w is not None:
                inner += w.actions()
                if hasattr(w, "menu") and w.menu() is not None:
                    inner += w.menu().actions()
                if hasattr(w, "defaultAction") and w.defaultAction() is not None:
                    inner.append(w.defaultAction())
            return any(x in reachable for x in inner if not x.isSeparator())
        return False

    for name in toolbars.HIDDEN_NATIVE:
        tb = win.findChild(QToolBar, name)
        if tb is None:
            continue
        for a in tb.actions():
            if a.isSeparator() or not a.objectName() or a.objectName() in later:
                continue
            check(covered(tb, a), "%s from %s not reachable" % (a.objectName(), name))

if failures:
    print("FAIL")
    for f in failures:
        print(" -", f)
else:
    print("PASS")
