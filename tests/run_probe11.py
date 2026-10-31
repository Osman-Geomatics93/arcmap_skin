"""Check the Measure window releases its map tool on plugin unload."""

import os
import traceback

from qgis.PyQt.QtCore import QEventLoop, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe11_result.txt")
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run():
    import qgis.utils as utils
    from qgis.core import QgsProject
    from qgis.PyQt.QtWidgets import QApplication

    iface = utils.iface
    canvas = iface.mapCanvas()
    try:
        utils.loadPlugin("arcmap_skin")
        utils.startPlugin("arcmap_skin")
        plugin = utils.plugins.get("arcmap_skin")
        for _ in range(40):
            wait(500)
            if plugin.on:
                break
        plugin.actions["measure_window"].trigger()
        wait(300)
        from arcmap_skin import measure

        mw = measure._window
        mw.feature_button.click()
        wait(200)
        lines.append("before unload: tool=%s used=%s visible=%s" % (canvas.mapTool().__class__.__name__, getattr(mw, "tool_used", None), mw.isVisible()))
        tops = [w.objectName() for w in QApplication.topLevelWidgets() if w.isVisible() and w.objectName().startswith("ArcMap")]
        lines.append("visible ArcMap windows: %s" % tops)
        utils.unloadPlugin("arcmap_skin")
        wait(500)
        lines.append("after unload: tool=%s" % (canvas.mapTool().__class__.__name__ if canvas.mapTool() else None))
        tops = [w.objectName() for w in QApplication.topLevelWidgets() if w.isVisible() and w.objectName().startswith("ArcMap")]
        lines.append("visible ArcMap windows after unload: %s" % tops)
    except Exception:
        lines.append(traceback.format_exc())
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().setDirty(False)
    iface.mainWindow().close()


QTimer.singleShot(1500, run)
