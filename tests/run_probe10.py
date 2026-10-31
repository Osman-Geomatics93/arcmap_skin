"""Reinstall regression: use the Edit Tool, zoom, unload the plugin (as the
plugin manager does on reinstall), reload it, then click on the map. QGIS
must survive. Writes probe10_result.txt."""

import os
import traceback

from qgis.PyQt.QtCore import QEventLoop, Qt, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe10_result.txt")
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def write():
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def run():
    import qgis.utils as utils
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer
    from qgis.PyQt.QtTest import QTest

    iface = utils.iface
    win = iface.mainWindow()
    canvas = iface.mapCanvas()
    try:
        utils.loadPlugin("arcmap_skin")
        utils.startPlugin("arcmap_skin")
        plugin = utils.plugins.get("arcmap_skin")
        for _ in range(40):
            wait(500)
            if plugin.on:
                break
        layer = QgsVectorLayer("Polygon?crs=EPSG:4326&field=name:string", "Districts", "memory")
        f = QgsFeature(layer.fields())
        f.setGeometry(QgsGeometry.fromPolygonXY([[QgsPointXY(30, 30), QgsPointXY(32, 30), QgsPointXY(32, 31), QgsPointXY(30, 31)]]))
        f.setAttributes(["Delta"])
        layer.dataProvider().addFeatures([f])
        QgsProject.instance().addMapLayer(layer)
        canvas.zoomToFullExtent()
        wait(800)
        layer.startEditing()
        plugin.actions["edit_tool"].trigger()
        wait(200)
        lines.append("edit tool current: %s" % canvas.mapTool().__class__.__name__)
        centre = canvas.rect().center()
        QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
        wait(300)
        lines.append("selected after click: %d" % layer.selectedFeatureCount())
        iface.actionZoomIn().trigger()
        wait(200)
        lines.append("zoom tool current: %s" % canvas.mapTool().__class__.__name__)
        # measure feature tool too
        plugin.actions["measure_window"].trigger()
        wait(300)
        from arcmap_skin import measure

        measure._window.feature_button.click()
        wait(200)
        layer.rollBack()
        # reinstall = unload + load while running
        for _ in range(3):
            utils.unloadPlugin("arcmap_skin")
            wait(500)
            lines.append("unloaded; current tool: %s" % (canvas.mapTool().__class__.__name__ if canvas.mapTool() else None))
            utils.loadPlugin("arcmap_skin")
            utils.startPlugin("arcmap_skin")
            plugin = utils.plugins.get("arcmap_skin")
            for _ in range(40):
                wait(500)
                if plugin.on:
                    break
            lines.append("reloaded on=%s" % plugin.on)
            write()
            for _ in range(3):
                QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
                QTest.mouseMove(canvas.viewport(), centre + __import__("qgis.PyQt.QtCore", fromlist=["QPoint"]).QPoint(20, 20))
                wait(200)
            iface.actionZoomIn().trigger()
            QTest.mouseClick(canvas.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
            wait(400)
            lines.append("survived clicks after reload %s; tool now %s" % (_, canvas.mapTool().__class__.__name__ if canvas.mapTool() else None))
            write()
            plugin.actions["edit_tool"].trigger()
            wait(200)
        lines.append("ALL OK")
    except Exception:
        lines.append(traceback.format_exc())
    write()
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    win.close()


QTimer.singleShot(1500, run)
