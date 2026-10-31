from qgis.PyQt.QtCore import QEventLoop, QTimer
OUT = "D:/QGIS_Plugins/Arcmap_Skin/tests/probe9_result.txt"
lines = []
def wait(ms):
    loop = QEventLoop(); QTimer.singleShot(ms, loop.quit); loop.exec()
def dump():
    from qgis.PyQt.QtWidgets import QApplication, QFrame, QListWidget, QStackedWidget, QTreeWidget
    w = QApplication.activeModalWidget()
    lines.append("modal: %s %s" % (w.metaObject().className() if w else None, w.objectName() if w else None))
    if w is None:
        return
    for cls in (QListWidget, QStackedWidget, QTreeWidget):
        for c in w.findChildren(cls):
            if c.objectName().startswith("mOptions") or c.objectName().startswith("mOpt"):
                lines.append("  %s %r parent=%r" % (cls.__name__, c.objectName(), c.parent().objectName() if c.parent() else None))
    for c in w.findChildren(QFrame):
        if c.objectName().startswith("mOptions"):
            lines.append("  QFrame %r parent=%r" % (c.objectName(), c.parent().objectName() if c.parent() else None))
    lw = w.findChild(QListWidget, "mOptionsListWidget")
    if lw is not None:
        lines.append("  pages: %s" % [lw.item(i).text() for i in range(lw.count())])
    tw = w.findChild(QTreeWidget, "mOptionsTreeView") or w.findChild(QTreeWidget)
    if tw is not None:
        lines.append("  tree %r top items: %s" % (tw.objectName(), [tw.topLevelItem(i).text(0) for i in range(tw.topLevelItemCount())]))
    w.reject()
def run():
    import qgis.utils as utils
    from qgis.core import QgsProject
    QTimer.singleShot(2500, dump)
    utils.iface.showOptionsDialog()
    wait(500)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().setDirty(False)
    utils.iface.mainWindow().close()
QTimer.singleShot(1500, run)
