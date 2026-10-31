"""Dump layout designer and symbol selector internals. Writes probe14_result.txt."""

import os
import traceback

from qgis.PyQt.QtCore import QEventLoop, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe14_result.txt")
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def dump_symbol_dialog():
    from qgis.PyQt.QtWidgets import QApplication, QComboBox, QPushButton, QToolButton, QWidget

    w = QApplication.activeModalWidget()
    lines.append("symbol modal: %s %s title=%r" % (w.metaObject().className() if w else None, w.objectName() if w else None, w.windowTitle() if w else None))
    if w is None:
        return
    for c in w.findChildren(QWidget):
        cls = c.metaObject().className()
        if cls.startswith("Qgs") and c.objectName():
            lines.append("  %s %r" % (cls, c.objectName()))
    for b in w.findChildren(QPushButton) + w.findChildren(QToolButton):
        if b.text():
            lines.append("  button %r %r" % (b.objectName(), b.text()))
    for cb in w.findChildren(QComboBox):
        if cb.objectName():
            lines.append("  combo %r items=%s" % (cb.objectName(), [cb.itemText(i) for i in range(min(cb.count(), 6))]))
    w.reject()


def run():
    import qgis.utils as utils
    from qgis.core import QgsPrintLayout, QgsProject, QgsVectorLayer
    from qgis.PyQt.QtGui import QAction
    from qgis.PyQt.QtWidgets import QToolBar

    iface = utils.iface
    try:
        layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string", "Probe", "memory")
        QgsProject.instance().addMapLayer(layer)
        layout = QgsPrintLayout(QgsProject.instance())
        layout.initializeDefaults()
        layout.setName("ProbeLayout")
        QgsProject.instance().layoutManager().addLayout(layout)
        designer = iface.openLayoutDesigner(layout)
        wait(1500)
        win = designer.window()
        lines.append("designer window: %s %s" % (win.metaObject().className(), win.objectName()))
        for tb in win.findChildren(QToolBar):
            if tb.parent() is win:
                lines.append("TB %s (%s): %s" % (tb.objectName(), tb.windowTitle(), [a.objectName() or a.text() for a in tb.actions()]))
        bar = win.menuBar()
        for act in bar.actions():
            m = act.menu()
            lines.append("MENU %s (%s): %s" % (m.objectName() if m else "-", act.text(), [a.objectName() or a.text() for a in m.actions()] if m else []))
        acts = [(a.objectName(), a.text()) for a in win.findChildren(QAction) if a.objectName().startswith("mAction")]
        lines.append("ACTIONS: %s" % acts)
        from qgis.PyQt.QtWidgets import QDockWidget

        lines.append("DOCKS: %s" % [(d.objectName(), d.windowTitle()) for d in win.findChildren(QDockWidget)])
        win.close()
        wait(300)
        # symbol selector dialog: open from the style manager? use QgsSymbolSelectorDialog directly
        from qgis.core import QgsMarkerSymbol, QgsStyle
        from qgis.gui import QgsSymbolSelectorDialog

        sym = QgsMarkerSymbol.createSimple({"name": "circle"})
        QTimer.singleShot(1500, dump_symbol_dialog)
        dlg = QgsSymbolSelectorDialog(sym, QgsStyle.defaultStyle(), layer, iface.mainWindow())
        dlg.exec()
    except Exception:
        lines.append(traceback.format_exc())
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    iface.mainWindow().close()


QTimer.singleShot(1500, run)
