"""Screenshot dialogs in the dark theme. Writes probe17_result.txt and screenshot_dark_*.png."""

import os
import traceback

from qgis.PyQt.QtCore import QEventLoop, QTimer
from qgis.PyQt.QtWidgets import QApplication, QDialog

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe17_result.txt")
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def shoot_modal(name):
    w = QApplication.activeModalWidget()
    lines.append("%s modal: %s" % (name, w.metaObject().className() if w else None))
    if w is None:
        return
    wait(300)
    w.grab().save(os.path.join(HERE, "screenshot_dark_%s.png" % name))
    w.reject()


def run():
    import qgis.utils as utils
    from qgis.core import QgsProject, QgsSettings, QgsVectorLayer

    iface = utils.iface
    try:
        if not utils.loadPlugin("arcmap_skin") or not utils.startPlugin("arcmap_skin"):
            raise RuntimeError("plugin did not load")
        wait(4000)
        plugin = utils.plugins.get("arcmap_skin")
        for d in iface.mainWindow().findChildren(QDialog):
            if d.isVisible() and "Getting Started" in d.windowTitle():
                d.reject()
        from arcmap_skin import settings

        layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string&field=pop:integer", "Probe", "memory")
        QgsProject.instance().addMapLayer(layer)
        QgsSettings().setValue(settings.KEY_THEME, "arcmap_dark")
        plugin.reapply()
        wait(1500)
        # 1. plugin's own options window
        plugin.actions["skin_options"].trigger()
        wait(600)
        own = iface.mainWindow().findChild(QDialog, "ArcMapSkinOptions")
        own.grab().save(os.path.join(HERE, "screenshot_dark_options.png"))
        own.close()
        wait(200)
        # 2. layer properties
        QTimer.singleShot(2500, lambda: shoot_modal("props"))
        iface.showLayerProperties(layer)
        wait(500)
        # 3. attribute table (non-modal)
        iface.showAttributeTable(layer)
        wait(1500)
        for w in QApplication.topLevelWidgets():
            if w.objectName().startswith("QgsAttributeTableDialog") or w.objectName() == "ArcMapAttributesDock":
                w.grab().save(os.path.join(HERE, "screenshot_dark_table.png"))
                lines.append("table window: %s" % w.objectName())
                w.close()
                break
        # 4. QGIS Options
        QTimer.singleShot(3000, lambda: shoot_modal("qgisoptions"))
        iface.showOptionsDialog(iface.mainWindow(), "mOptionsPageArcMapSkin")
        wait(500)
        # 5. message box
        from qgis.PyQt.QtWidgets import QMessageBox

        QTimer.singleShot(1200, lambda: shoot_modal("msgbox"))
        QMessageBox.information(iface.mainWindow(), "ArcMap Skin", "Dark message box")
        QgsSettings().setValue(settings.KEY_THEME, "arcmap_light")
        plugin.reapply()
        wait(1500)
    except Exception:
        lines.append(traceback.format_exc())
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    iface.mainWindow().close()


QTimer.singleShot(4000, run)
