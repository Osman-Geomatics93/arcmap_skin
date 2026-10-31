"""Reinstall from ZIP *inside the Plugin Manager dialog* (the real user
path), then click on many widgets. Writes probe13_result.txt progressively."""

import os
import traceback

from qgis.PyQt.QtCore import QEventLoop, QPoint, Qt, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe13_result.txt")
ZIP = "D:/QGIS_Plugins/Arcmap_Skin/dist/arcmap_skin-0.1.0.zip"
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def step(text):
    lines.append(text)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def click_widgets(iface, tag):
    from qgis.PyQt.QtTest import QTest
    from qgis.PyQt.QtWidgets import QAbstractButton, QDockWidget, QMenu, QToolBar, QToolButton, QTreeView, QTreeWidget, QWidget

    win = iface.mainWindow()
    canvas = iface.mapCanvas()
    centre = canvas.rect().center()
    QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
    QTest.mouseMove(canvas.viewport(), centre + QPoint(15, 15))
    wait(150)
    step("%s: canvas ok" % tag)
    view = iface.layerTreeView()
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(40, 10))
    QTimer.singleShot(400, lambda: [m.close() for m in win.findChildren(QMenu) if m.isVisible()])
    QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, QPoint(40, 10))
    wait(700)
    step("%s: TOC ok" % tag)
    header = win.findChild(QWidget, "ArcMapTocHeader")
    if header is not None:
        for b in header.findChildren(QToolButton):
            QTest.mouseClick(b, Qt.MouseButton.LeftButton)
            wait(120)
        step("%s: List By buttons ok" % tag)
    for name in ("ArcMapStandardToolBar", "ArcMapToolsToolBar", "ArcMapEditorToolBar", "ArcMapLabelingToolBar"):
        tb = win.findChild(QToolBar, name)
        if tb is None:
            continue
        for b in [b for b in tb.findChildren(QToolButton) if b.isVisible()][:6]:
            QTest.mouseMove(b, b.rect().center())
            wait(25)
        step("%s: hover %s ok" % (tag, name))
    bar = win.menuBar()
    for act in bar.actions()[:3]:
        rect = bar.actionGeometry(act)
        QTimer.singleShot(300, lambda: [m.close() for m in win.findChildren(QMenu) if m.isVisible()])
        QTest.mouseClick(bar, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, rect.center())
        wait(500)
    step("%s: menus ok" % tag)
    footer = win.centralWidget().findChild(QWidget, "ArcMapStatusBar")
    if footer is not None:
        for b in footer.findChildren(QAbstractButton):
            QTest.mouseMove(b, b.rect().center())
            wait(25)
        step("%s: status bar ok" % tag)
    for name in ("Browser", "ArcMapToolboxDock"):
        dock = win.findChild(QDockWidget, name)
        if dock is None:
            continue
        dock.show()
        dock.raise_()
        tree = dock.findChild(QTreeWidget) or dock.findChild(QTreeView)
        if tree is not None:
            QTest.mouseClick(tree.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(40, 12))
            wait(150)
        step("%s: dock %s ok" % (tag, name))
    # attribute table toolbar buttons
    from qgis.PyQt.QtWidgets import QApplication, QDialog

    for w in list(QApplication.topLevelWidgets()) + win.findChildren(QDialog):
        if w.objectName().startswith("QgsAttributeTableDialog") and w.isVisible():
            tb = w.findChild(QToolBar, "mToolbar")
            for b in [b for b in tb.findChildren(QToolButton) if b.isVisible()][:8]:
                QTest.mouseMove(b, b.rect().center())
                wait(25)
            footer = w.findChild(QWidget, "ArcMapTableFooter")
            if footer is not None:
                for b in footer.findChildren(QAbstractButton)[:4]:
                    QTest.mouseClick(b, Qt.MouseButton.LeftButton)
                    wait(60)
            step("%s: attribute table ok" % tag)
            break
    iface.actionZoomIn().trigger()
    QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
    wait(300)
    step("%s: zoom click ok; tool=%s" % (tag, canvas.mapTool().__class__.__name__ if canvas.mapTool() else None))


def reinstall_inside_manager():
    """Runs while the Plugin Manager dialog is modal, like a real reinstall."""
    from pyplugin_installer import instance
    from qgis.PyQt.QtWidgets import QApplication

    modal = QApplication.activeModalWidget()
    step("modal during reinstall: %s" % (modal.metaObject().className() if modal else None))
    try:
        instance().installFromZipFile(ZIP)
        step("installFromZipFile returned")
    except Exception:
        step(traceback.format_exc())
    # close the plugin manager (and any message boxes it opened) a bit later
    def close_manager():
        for w in QApplication.topLevelWidgets():
            if w.isVisible() and w.metaObject().className() in ("QgsPluginManager", "QMessageBox"):
                step("closing %s" % w.metaObject().className())
                w.close()
    QTimer.singleShot(1500, close_manager)
    QTimer.singleShot(4000, close_manager)


def run():
    import qgis.utils as utils
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer
    from qgis.PyQt.QtWidgets import QDockWidget

    iface = utils.iface
    win = iface.mainWindow()
    try:
        plugin = None
        for _ in range(300):
            wait(500)
            plugin = utils.plugins.get("arcmap_skin")
            if plugin is not None and plugin.on:
                break
        step("start: on=%s" % (plugin.on if plugin else None))
        layer = QgsVectorLayer("Polygon?crs=EPSG:4326&field=name:string", "Districts", "memory")
        f = QgsFeature(layer.fields())
        f.setGeometry(QgsGeometry.fromPolygonXY([[QgsPointXY(30, 30), QgsPointXY(32, 30), QgsPointXY(32, 31), QgsPointXY(30, 31)]]))
        f.setAttributes(["Delta"])
        layer.dataProvider().addFeatures([f])
        QgsProject.instance().addMapLayer(layer)
        iface.mapCanvas().zoomToFullExtent()
        wait(800)
        plugin.actions["edit_tool"].trigger()
        iface.showAttributeTable(layer)
        wait(800)
        click_widgets(iface, "before")
        # open the Plugin Manager (modal) and reinstall from inside it
        QTimer.singleShot(2500, reinstall_inside_manager)
        iface.actionManagePlugins().trigger()  # blocks until the dialog closes
        step("plugin manager closed")
        plugin = None
        for _ in range(300):
            wait(500)
            plugin = utils.plugins.get("arcmap_skin")
            if plugin is not None and plugin.on:
                break
        step("after reinstall: on=%s" % (plugin.on if plugin else None))
        wait(1500)
        from qgis.PyQt.QtWidgets import QApplication, QDialog

        for w in QApplication.topLevelWidgets():
            if isinstance(w, QDialog) and w.isVisible() and w.objectName() == "ArcMapGettingStarted":
                from qgis.PyQt.QtTest import QTest
                from qgis.PyQt.QtWidgets import QPushButton

                cancel = next((b for b in w.findChildren(QPushButton) if "Cancel" in b.text()), None)
                if cancel:
                    QTest.mouseClick(cancel, Qt.MouseButton.LeftButton)
                step("getting started closed by click")
        wait(500)
        click_widgets(iface, "after")
        step("ALL OK")
    except Exception:
        step(traceback.format_exc())
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    win.close()


QTimer.singleShot(1500, run)
