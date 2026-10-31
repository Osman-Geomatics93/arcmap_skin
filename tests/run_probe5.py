"""Dump the attribute table dialog internals. Writes probe5_result.txt."""

import os

from qgis.PyQt.QtCore import QEventLoop, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe5_result.txt")
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run():
    import qgis.utils as utils
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer
    from qgis.PyQt.QtWidgets import QApplication, QDialog, QToolBar, QToolButton, QWidget, QAbstractButton

    iface = utils.iface
    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string&field=value:int", "Cities", "memory")
    f = QgsFeature(layer.fields())
    f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(31, 30)))
    f.setAttributes(["Cairo", 1])
    layer.dataProvider().addFeatures([f])
    QgsProject.instance().addMapLayer(layer)
    iface.showAttributeTable(layer)
    wait(1000)
    dlg = None
    for w in list(QApplication.topLevelWidgets()) + iface.mainWindow().findChildren(QDialog):
        if w.objectName().startswith("QgsAttributeTableDialog"):
            dlg = w
            break
    lines.append("dialog: %s parent=%s" % (dlg.objectName() if dlg else None, type(dlg.parent()).__name__ if dlg and dlg.parent() else None))
    if dlg is not None:
        tb = dlg.findChild(QToolBar, "mToolbar")
        for a in tb.actions():
            w = tb.widgetForAction(a)
            lines.append("  action %r text=%r widget=%s" % (a.objectName(), a.text(), type(w).__name__ if w else None))
            if w is not None and isinstance(w, QToolButton) and w.menu() is not None:
                lines.append("     menu: %s" % [(x.objectName(), x.text()) for x in w.menu().actions()])
        for w in dlg.findChildren(QWidget):
            cls = w.metaObject().className()
            if cls in ("QgsAttributeTableView", "QgsDualView", "QgsFeatureFilterWidget", "QTableView", "QgsFilterLineEdit", "QgsAttributeTableFilterModel") or w.objectName() in ("mFilterButton", "mMainView", "mTableViewButton", "mAttributeViewButton", "mFeatureFilterWidget"):
                lines.append("  widget %r class=%s parent=%s" % (w.objectName(), cls, w.parent().objectName() if w.parent() else None))
        for b in dlg.findChildren(QAbstractButton):
            if b.objectName():
                lines.append("  button %r text=%r class=%s" % (b.objectName(), b.text(), b.metaObject().className()))
        lines.append("  layout: %s rows=%s" % (type(dlg.layout()).__name__, getattr(dlg.layout(), "rowCount", lambda: None)()))
        # header / view signals
        from qgis.gui import QgsAttributeTableView, QgsDualView
        from qgis.PyQt import sip
        view = dlg.findChild(QWidget, "mMainView")
        try:
            dual = sip.cast(view, QgsDualView)
            tv = dual.tableView()
            lines.append("  tableView class=%s objectName=%r horizontalHeader=%s" % (tv.metaObject().className(), tv.objectName(), tv.horizontalHeader().metaObject().className()))
            lines.append("  tableView contextMenuPolicy=%s header policy=%s" % (int(tv.contextMenuPolicy()), int(tv.horizontalHeader().contextMenuPolicy())))
            lines.append("  model class=%s" % tv.model().metaObject().className())
            lines.append("  has columnContextMenuRequested: %s" % hasattr(tv, "columnContextMenuRequested"))
        except Exception as exc:
            lines.append("  dual cast failed: %s" % exc)
        from qgis.core import QgsSettings
        lines.append("  dockAttributeTable setting=%r" % QgsSettings().value("qgis/dockAttributeTable"))
        dlg.close()
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    iface.mainWindow().close()


QTimer.singleShot(1500, run)
