"""Exercise the new windows (magnifier, measure, customize, attributes, label
manager, project properties tabs, symbology tree). Writes probe8_result.txt
and screenshots."""

import os
import traceback

from qgis.PyQt.QtCore import QEventLoop, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe8_result.txt")
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def inspect_modal(tag):
    from qgis.PyQt.QtWidgets import QApplication, QTabBar, QTreeWidget

    w = QApplication.activeModalWidget()
    if w is None:
        lines.append("[%s] no modal" % tag)
        return
    import qgis.utils as utils
    from arcmap_skin import dialogs

    plugin = utils.plugins.get("arcmap_skin")
    dialogs.dress_layer_properties(plugin.changes, w, utils.iface)
    dialogs.dress_renderer_combos(w)
    wait(300)
    bar = w.findChild(QTabBar, "ArcMapPropertyTabBar")
    lines.append("[%s] %s tabs=%s" % (tag, w.metaObject().className(), [bar.tabText(i) for i in range(bar.count())] if bar else None))
    trees = [t for t in w.findChildren(QTreeWidget) if t.parent() and t.parent().objectName() == "ArcMapSymbologyTree"]
    lines.append("[%s] symbology tree present=%s" % (tag, bool(trees)))
    if trees and bar:
        bar.setCurrentIndex(3)
        wait(400)
        w.resize(950, 640)
        wait(300)
        w.grab().save(os.path.join(HERE, "screenshot_symbology.png"))
    w.reject()


def run():
    import qgis.utils as utils
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer
    from qgis.PyQt.QtWidgets import QDockWidget

    iface = utils.iface
    win = iface.mainWindow()
    try:
        utils.loadPlugin("arcmap_skin")
        utils.startPlugin("arcmap_skin")
        plugin = utils.plugins.get("arcmap_skin")
        for _ in range(40):
            wait(500)
            if plugin.on:
                break
        layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string", "Cities", "memory")
        f = QgsFeature(layer.fields())
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(31, 30)))
        f.setAttributes(["Cairo"])
        layer.dataProvider().addFeatures([f])
        QgsProject.instance().addMapLayer(layer)
        layer.selectAll()
        acts = plugin.actions
        # windows
        acts["magnifier"].trigger()
        wait(800)
        from arcmap_skin import magnifier, measure

        lines.append("magnifier open=%s" % (magnifier._window is not None and magnifier._window.isVisible()))
        magnifier._window.grab().save(os.path.join(HERE, "screenshot_magnifier.png"))
        magnifier._window.close()
        acts["measure_window"].trigger()
        wait(500)
        mw = measure._window
        lines.append("measure open=%s" % (mw is not None and mw.isVisible()))
        mw.report_feature(layer.getFeature(1), layer)
        lines.append("measure text=%r" % mw.results.toPlainText()[:60])
        mw.close()
        acts["customize"].trigger()
        wait(500)
        from qgis.PyQt.QtWidgets import QApplication, QDialog

        cz = next((d for d in QApplication.topLevelWidgets() if isinstance(d, QDialog) and d.objectName() == "ArcMapCustomize"), None)
        lines.append("customize open=%s toolbars listed=%s commands=%s" % (cz is not None, cz.tb_list.count() if cz else None, cz.cmd_list.count() if cz else None))
        if cz:
            cz.grab().save(os.path.join(HERE, "screenshot_customize.png"))
            cz.close()
        # docks
        layer.startEditing()
        attrs = win.findChild(QDockWidget, "ArcMapAttributesDock")
        attrs.show()
        attrs.raise_()
        wait(600)
        lines.append("attributes tree items=%d form=%s" % (attrs.tree.topLevelItemCount(), attrs.form is not None))
        attrs.grab().save(os.path.join(HERE, "screenshot_attributes.png"))
        lm = win.findChild(QDockWidget, "ArcMapLabelManagerDock")
        lm.show()
        lm.raise_()
        wait(400)
        lines.append("label manager layers=%d" % lm.tree.topLevelItemCount())
        lm.tree.topLevelItem(0).setCheckState(0, __import__("qgis.PyQt.QtCore", fromlist=["Qt"]).Qt.CheckState.Checked)
        wait(200)
        lines.append("labels enabled after check=%s" % layer.labelsEnabled())
        acts["pause_labeling"].setChecked(True)
        wait(200)
        acts["pause_labeling"].setChecked(False)
        # edit tool
        acts["edit_tool"].trigger()
        wait(200)
        lines.append("edit tool active=%s" % (iface.mapCanvas().mapTool().__class__.__name__))
        layer.rollBack()
        # dialogs with tabs
        QTimer.singleShot(2500, lambda: inspect_modal("layer"))
        iface.showLayerProperties(layer)
        wait(500)
        QTimer.singleShot(2500, lambda: inspect_modal("project"))
        iface.showProjectPropertiesDialog()
        wait(500)
        QTimer.singleShot(2500, lambda: inspect_modal("options"))
        iface.showOptionsDialog()
        wait(500)
        # identify dock
        from qgis.PyQt.QtWidgets import QComboBox

        iface.mapCanvas().setSelectionColor(iface.mapCanvas().selectionColor())
        idock = win.findChild(QDockWidget, "IdentifyResultsDock")
        lines.append("identify dock present=%s combo=%s" % (idock is not None, idock.findChild(QComboBox, "ArcMapIdentifyFrom") is not None if idock else None))
        # status bar drawing label
        from qgis.PyQt.QtWidgets import QLabel

        lines.append("drawing label present=%s" % (win.centralWidget().findChild(QLabel, "ArcMapDrawingLabel") is not None))
    except Exception:
        lines.append(traceback.format_exc())
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    QTimer.singleShot(1500, lambda: [w.reject() for w in __import__("qgis.PyQt.QtWidgets", fromlist=["QApplication"]).QApplication.topLevelWidgets() if hasattr(w, "reject") and w.isVisible() and w is not win])
    win.close()


QTimer.singleShot(1500, run)
