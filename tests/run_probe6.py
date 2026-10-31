"""Dump the layer properties dialog structure (vector + raster). Writes probe6_result.txt."""

import os

from qgis.PyQt.QtCore import QEventLoop, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe6_result.txt")
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def dump_modal(tag):
    from qgis.PyQt.QtWidgets import QApplication, QFrame, QLineEdit, QListWidget, QSplitter, QStackedWidget, QDialogButtonBox

    w = QApplication.activeModalWidget()
    lines.append("[%s] modal: %s %s title=%r" % (tag, w.metaObject().className() if w else None, w.objectName() if w else None, w.windowTitle() if w else None))
    if w is None:
        return
    lines.append("  layout: %s" % type(w.layout()).__name__)
    for cls in (QSplitter, QStackedWidget, QListWidget, QLineEdit, QDialogButtonBox):
        for c in w.findChildren(cls):
            if c.objectName():
                lines.append("  %s %r parent=%r" % (cls.__name__, c.objectName(), c.parent().objectName() if c.parent() else None))
    for c in w.findChildren(QFrame):
        if c.objectName().startswith("mOptions"):
            lines.append("  QFrame %r parent=%r layout=%s" % (c.objectName(), c.parent().objectName() if c.parent() else None, type(c.layout()).__name__ if c.layout() else None))
    lw = w.findChild(QListWidget, "mOptionsListWidget")
    st = w.findChild(QStackedWidget, "mOptStackedWidget")
    if lw is not None and st is not None:
        lines.append("  pages: %s" % [(i, lw.item(i).text(), st.widget(i).objectName()) for i in range(lw.count())])
        lines.append("  list count=%d stack count=%d" % (lw.count(), st.count()))
        frame = w.findChild(QFrame, "mOptionsFrame")
        if frame is not None and frame.layout() is not None:
            lay = frame.layout()
            lines.append("  mOptionsFrame layout items: %s" % [(type(lay.itemAt(i).widget()).__name__ if lay.itemAt(i).widget() else "layout", lay.itemAt(i).widget().objectName() if lay.itemAt(i).widget() else "") for i in range(lay.count())])
    w.reject()


def run():
    import qgis.utils as utils
    from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer

    iface = utils.iface
    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string", "Probe", "memory")
    QgsProject.instance().addMapLayer(layer)
    QTimer.singleShot(2500, lambda: dump_modal("vector"))
    iface.showLayerProperties(layer)
    wait(500)
    # raster: a tiny generated raster via processing is heavy; use the QGIS test if exists
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "arcmap_probe6.tif")
    try:
        from osgeo import gdal
        drv = gdal.GetDriverByName("GTiff")
        ds = drv.Create(path, 4, 4, 1, gdal.GDT_Byte)
        ds.SetGeoTransform((30, 0.1, 0, 31, 0, -0.1))
        ds.GetRasterBand(1).WriteArray(__import__("numpy").zeros((4, 4), dtype="uint8"))
        ds = None
        rl = QgsRasterLayer(path, "ProbeRaster")
        QgsProject.instance().addMapLayer(rl)
        QTimer.singleShot(2500, lambda: dump_modal("raster"))
        iface.showLayerProperties(rl)
        wait(500)
    except Exception as exc:
        lines.append("raster failed: %s" % exc)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    iface.mainWindow().close()


QTimer.singleShot(1500, run)
