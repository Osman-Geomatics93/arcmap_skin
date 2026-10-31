"""Reproduce "Install from ZIP" over a running plugin, then click around.
Writes probe12_result.txt progressively so a crash shows the last step."""

import os
import traceback

from qgis.PyQt.QtCore import QEventLoop, QPoint, Qt, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe12_result.txt")
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


def click_around(iface, tag):
    from qgis.PyQt.QtTest import QTest
    from qgis.PyQt.QtWidgets import QToolBar, QToolButton, QMenu

    win = iface.mainWindow()
    canvas = iface.mapCanvas()
    centre = canvas.rect().center()
    QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
    QTest.mouseMove(canvas.viewport(), centre + QPoint(15, 15))
    wait(150)
    step("%s: canvas click ok" % tag)
    view = iface.layerTreeView()
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(40, 10))
    wait(150)
    step("%s: TOC click ok" % tag)
    # right-click TOC (context menu) and close it
    QTimer.singleShot(400, lambda: [m.close() for m in win.findChildren(QMenu) if m.isVisible()])
    QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, QPoint(40, 10))
    wait(700)
    step("%s: TOC right-click ok" % tag)
    for name in ("ArcMapStandardToolBar", "ArcMapToolsToolBar", "ArcMapEditorToolBar"):
        tb = win.findChild(QToolBar, name)
        if tb is None:
            step("%s: toolbar %s missing" % (tag, name))
            continue
        buttons = [b for b in tb.findChildren(QToolButton) if b.isVisible() and b.defaultAction() is not None and b.defaultAction().menu() is None]
        for b in buttons[:4]:
            QTest.mouseMove(b, b.rect().center())
            wait(30)
        step("%s: hover %s ok (%d buttons)" % (tag, name, len(buttons)))
    # open and close File menu via the menubar
    bar = win.menuBar()
    first = bar.actions()[0]
    rect = bar.actionGeometry(first)
    QTimer.singleShot(400, lambda: [m.close() for m in win.findChildren(QMenu) if m.isVisible()])
    QTest.mouseClick(bar, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, rect.center())
    wait(700)
    step("%s: menubar click ok (%s)" % (tag, first.text()))
    # zoom tool then click on canvas (returns to the last tool)
    iface.actionZoomIn().trigger()
    QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
    wait(300)
    step("%s: zoom click ok; tool=%s" % (tag, canvas.mapTool().__class__.__name__ if canvas.mapTool() else None))
    iface.actionPan().trigger()


def run():
    import qgis.utils as utils
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer
    from qgis.PyQt.QtWidgets import QDockWidget

    iface = utils.iface
    win = iface.mainWindow()
    try:
        plugin = utils.plugins.get("arcmap_skin")
        step("plugin loaded at startup: %s" % (plugin is not None))
        for _ in range(300):
            wait(500)
            plugin = utils.plugins.get("arcmap_skin")
            if plugin is not None and plugin.on:
                break
        step("on=%s" % (plugin.on if plugin else None))
        layer = QgsVectorLayer("Polygon?crs=EPSG:4326&field=name:string", "Districts", "memory")
        f = QgsFeature(layer.fields())
        f.setGeometry(QgsGeometry.fromPolygonXY([[QgsPointXY(30, 30), QgsPointXY(32, 30), QgsPointXY(32, 31), QgsPointXY(30, 31)]]))
        f.setAttributes(["Delta"])
        layer.dataProvider().addFeatures([f])
        QgsProject.instance().addMapLayer(layer)
        iface.mapCanvas().zoomToFullExtent()
        wait(800)
        # use a few things first, like a real session
        plugin.actions["edit_tool"].trigger()
        wait(200)
        iface.showAttributeTable(layer)
        wait(800)
        win.findChild(QDockWidget, "ArcMapToolboxDock").show()
        click_around(iface, "before")
        # the real thing: Plugin Manager > Install from ZIP
        from pyplugin_installer import instance

        installer = instance()
        step("installing from zip…")
        installer.installFromZipFile(ZIP)
        wait(1000)
        plugin = utils.plugins.get("arcmap_skin")
        for _ in range(300):
            wait(500)
            plugin = utils.plugins.get("arcmap_skin")
            if plugin is not None and plugin.on:
                break
        step("after reinstall: loaded=%s on=%s" % (plugin is not None, plugin.on if plugin else None))
        from qgis.PyQt.QtWidgets import QApplication, QDialog

        for w in QApplication.topLevelWidgets():
            if isinstance(w, QDialog) and w.isVisible():
                step("closing dialog: %s %s" % (w.metaObject().className(), w.objectName()))
                w.close()
        wait(300)
        click_around(iface, "after")
        step("ALL OK")
    except Exception:
        step(traceback.format_exc())
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    win.close()


QTimer.singleShot(1500, run)
