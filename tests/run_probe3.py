"""Probe the Getting Started dialog / exit behaviour. Writes probe3_result.txt."""

import os

from qgis.PyQt.QtCore import QEventLoop, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe3_result.txt")
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def dump(tag):
    from qgis.core import QgsProject
    from qgis.PyQt.QtWidgets import QApplication

    tops = [(w.metaObject().className(), w.objectName()) for w in QApplication.topLevelWidgets() if w.isVisible() and w.isWindow()]
    lines.append("[%s] project=%r dirty=%s tops=%s" % (tag, QgsProject.instance().fileName(), QgsProject.instance().isDirty(), tops))


def run():
    import qgis.utils as utils
    from qgis.core import QgsProject, QgsSettings
    from qgis.PyQt.QtWidgets import QApplication, QDialog

    QgsSettings().setValue("arcmap_skin/show_getting_started", True)
    utils.loadPlugin("arcmap_skin")
    utils.startPlugin("arcmap_skin")
    plugin = utils.plugins.get("arcmap_skin")
    for _ in range(40):
        wait(500)
        if plugin.on:
            break
    lines.append("on=%s" % plugin.on)
    dump("after enable")
    wait(2500)
    dump("after 2.5s")
    gs = next((w for w in QApplication.topLevelWidgets() if isinstance(w, QDialog) and w.objectName() == "ArcMapGettingStarted"), None)
    lines.append("getting started visible=%s" % (gs is not None and gs.isVisible()))
    if gs is not None:
        item = gs.list.currentItem()
        lines.append("current item=%r data=%r" % (item.text() if item else None, item.data(gs.list.currentItem().data(0x0100 + 9) and 0 or 0x0100 + 9) if item else None))
        gs.reject()
        wait(500)
    dump("after reject")
    win = utils.iface.mainWindow()
    QgsProject.instance().setDirty(False)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QTimer.singleShot(3000, lambda: (dump("3s after close"), open(OUT, "a", encoding="utf-8").write(lines[-1] + "\n")))
    win.close()
    lines.append("close() returned; window visible=%s" % win.isVisible())
    with open(OUT, "a", encoding="utf-8") as fh:
        fh.write(lines[-1] + "\n")


QTimer.singleShot(1500, run)
