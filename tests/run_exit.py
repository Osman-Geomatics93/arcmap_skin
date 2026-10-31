"""Exit check: start QGIS with ``--code tests/run_exit.py``.

Switches the look on, adds layers, then closes the main window the normal
way (close event → fileExit → closeProject). QGIS must exit with code 0.
"""

import os

from qgis.PyQt.QtCore import QEventLoop, QTimer
from qgis.PyQt.QtWidgets import QApplication

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "exit_result.txt")


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run():
    import qgis.utils as utils
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer

    utils.loadPlugin("arcmap_skin")
    utils.startPlugin("arcmap_skin")
    wait(500)
    plugin = utils.plugins.get("arcmap_skin")
    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string", "Cities", "memory")
    f = QgsFeature(layer.fields())
    f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(31.2, 30.0)))
    f.setAttributes(["Cairo"])
    layer.dataProvider().addFeatures([f])
    QgsProject.instance().addMapLayer(layer)
    utils.iface.mapCanvas().zoomToFullExtent()
    wait(1500)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("on=%s layers=%d; closing main window normally\n" % (plugin.on, len(QgsProject.instance().mapLayers())))
    QgsProject.instance().setDirty(False)
    utils.iface.mainWindow().close()


QTimer.singleShot(1500, run)
