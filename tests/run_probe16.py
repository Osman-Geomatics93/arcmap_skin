"""Change the theme from the Options dialog with OK while a modal box is open (crash regression).

Writes probe16_result.txt.
"""

import os
import traceback

from qgis.PyQt.QtCore import QEventLoop, QTimer
from qgis.PyQt.QtWidgets import QApplication, QComboBox, QDialog, QDialogButtonBox, QMessageBox, QWidget

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe16_result.txt")
lines = []
from qgis.core import QgsApplication  # noqa: E402

QgsApplication.messageLog().messageReceived.connect(lambda m, t, l: lines.append("[%s] %s" % (t, m)))


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def press_ok():
    dlg = QApplication.activeModalWidget()
    lines.append("options modal: %s" % (dlg.metaObject().className() if dlg else None))
    if dlg is None:
        return
    page = dlg.findChild(QWidget, "mOptionsPageArcMapSkin")
    combo = page.findChild(QComboBox) if page else None
    if combo is None:
        lines.append("no theme combo")
        dlg.reject()
        return
    combo.setCurrentIndex(combo.findData("arcmap_dark"))
    lines.append("combo set: index=%s data=%s" % (combo.currentIndex(), combo.currentData()))
    # A message box like the one Processing shows while the pages are saved:
    # it opens right after accept() starts and closes itself a second later.
    def nag():
        box = QMessageBox(QMessageBox.Icon.Warning, "Processing", "Nested modal during save", QMessageBox.StandardButton.Ok, dlg)
        QTimer.singleShot(1200, box.accept)
        box.exec()
    QTimer.singleShot(0, nag)
    # QgsOptions saves its pages from the button box's accepted signal, so
    # click the real OK button rather than calling accept().
    ok = dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)
    ok.click()
    lines.append("OK clicked: result=%s visible=%s" % (dlg.result(), dlg.isVisible()))


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
        from arcmap_skin import settings, util

        QgsSettings().setValue(settings.KEY_THEME, "arcmap_light")
        layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string", "Probe", "memory")
        QgsProject.instance().addMapLayer(layer)
        lines.append("before: theme=%s on=%s" % (settings.theme(), plugin.on))
        QTimer.singleShot(2500, press_ok)
        plugin.actions["skin_options"].trigger()
        lines.append("dialog closed: theme=%s modal=%s" % (settings.theme(), QApplication.activeModalWidget() is not None))
        wait(300)
        lines.append("300ms later: icon_dir=%s busy=%s" % (os.path.basename(util._icon_dir()), plugin._busy))
        wait(4000)
        lines.append("after: on=%s icon_dir=%s dark_css=%s timer=%s" % (
            plugin.on, os.path.basename(util._icon_dir()), "#2b2b2b" in QApplication.instance().styleSheet(), plugin._reapply_timer))
        QgsSettings().setValue(settings.KEY_THEME, "arcmap_light")
        plugin.reapply()
        wait(1500)
        lines.append("restored: icon_dir=%s" % os.path.basename(util._icon_dir()))
    except Exception:
        lines.append(traceback.format_exc())
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    iface.mainWindow().close()


QTimer.singleShot(4000, run)
