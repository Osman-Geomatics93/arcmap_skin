"""Regression probe: double-click a recent map in Getting Started must not crash.
Writes probe4_result.txt; QGIS must exit normally afterwards."""

import os
import tempfile

from qgis.PyQt.QtCore import QEventLoop, Qt, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe4_result.txt")
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run():
    import qgis.utils as utils
    from qgis.core import QgsProject, QgsVectorLayer
    from qgis.PyQt.QtTest import QTest
    from qgis.PyQt.QtWidgets import QListWidgetItem

    utils.loadPlugin("arcmap_skin")
    utils.startPlugin("arcmap_skin")
    plugin = utils.plugins.get("arcmap_skin")
    for _ in range(40):
        wait(500)
        if plugin.on:
            break
    # a project file to open
    project = QgsProject.instance()
    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string", "Probe", "memory")
    project.addMapLayer(layer)
    path = os.path.join(tempfile.gettempdir(), "arcmap_probe4.qgz")
    project.write(path)
    project.clear()
    wait(500)
    from arcmap_skin.getting_started import GettingStartedDialog, PATH_ROLE

    gs = GettingStartedDialog(utils.iface)
    gs.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    gs.show()
    wait(500)
    gs.list.clear()
    item = QListWidgetItem("probe project")
    item.setData(PATH_ROLE, path)
    gs.list.addItem(item)
    rect = gs.list.visualItemRect(item)
    QTest.mouseClick(gs.list.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, rect.center())
    QTest.mouseDClick(gs.list.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, rect.center())
    wait(3000)
    lines.append("project after double-click: %r layers=%d" % (project.fileName(), len(project.mapLayers())))
    lines.append("survived double-click: True")
    project.clear()
    project.setDirty(False)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    utils.iface.mainWindow().close()


QTimer.singleShot(1500, run)

