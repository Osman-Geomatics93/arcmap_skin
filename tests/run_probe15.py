"""Probe the settings page, dark theme and translations. Writes probe15_result.txt."""

import os
import traceback

from qgis.PyQt.QtCore import QEventLoop, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe15_result.txt")
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def dump_options():
    from qgis.PyQt.QtWidgets import QApplication, QCheckBox, QComboBox, QWidget

    w = QApplication.activeModalWidget()
    lines.append("options modal: %s" % (w.metaObject().className() if w else None))
    if w is None:
        return
    page = w.findChild(QWidget, "mOptionsPageArcMapSkin")
    lines.append("skin page found: %s" % (page is not None))
    if page is not None:
        lines.append("  checkboxes: %d" % len(page.findChildren(QCheckBox)))
        combo = page.findChild(QComboBox)
        lines.append("  theme combo: %s" % [combo.itemText(i) for i in range(combo.count())] if combo else "none")
    w.reject()


def run():
    import qgis.utils as utils
    from qgis.core import QgsProject, QgsSettings, QgsVectorLayer
    from qgis.PyQt.QtCore import QCoreApplication, QTranslator

    iface = utils.iface
    try:
        if not utils.loadPlugin("arcmap_skin") or not utils.startPlugin("arcmap_skin"):
            raise RuntimeError("plugin did not load")
        wait(4000)
        plugin = utils.plugins.get("arcmap_skin")
        from qgis.PyQt.QtWidgets import QDialog

        for d in iface.mainWindow().findChildren(QDialog):
            if d.isVisible() and "Getting Started" in d.windowTitle():
                d.reject()
        layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string", "Probe", "memory")
        QgsProject.instance().addMapLayer(layer)
        lines.append("plugin on: %s" % plugin.on)
        # options page
        QTimer.singleShot(2500, dump_options)
        iface.showOptionsDialog(iface.mainWindow(), "mOptionsPageArcMapSkin")
        wait(500)
        # the ArcMap menu entry opens the plugin's own (non-modal) window
        from qgis.PyQt.QtWidgets import QDialog as _QDialog
        plugin.actions["skin_options"].trigger()
        wait(500)
        own = iface.mainWindow().findChild(_QDialog, "ArcMapSkinOptions")
        lines.append("own options window: %s visible=%s" % (own is not None, own.isVisible() if own else None))
        if own is not None:
            own.close()
            wait(200)
        # dark theme
        from arcmap_skin import settings, util

        QgsSettings().setValue(settings.KEY_THEME, "arcmap_dark")
        plugin.reapply()
        wait(1500)
        ss = QApplication.instance().styleSheet()
        lines.append("dark theme: icon_dir=%s stylesheet_has_dark=%s" % (os.path.basename(util._icon_dir()), "#2b2b2b" in ss or "2b2b2b" in ss))
        iface.mainWindow().grab().save(os.path.join(HERE, "screenshot_dark.png"))
        QgsSettings().setValue(settings.KEY_THEME, "arcmap_light")
        plugin.reapply()
        wait(1500)
        lines.append("light again: icon_dir=%s" % os.path.basename(util._icon_dir()))
        # translations
        for lang, probe in (("fr", "Zoom avant"), ("es", "Acercar"), ("tr", "Yakınlaştır"), ("ar", None)):
            t = QTranslator()
            ok = t.load(os.path.join("D:/QGIS_Plugins/Arcmap_Skin/arcmap_skin/i18n", "arcmap_skin_%s.qm" % lang))
            QCoreApplication.installTranslator(t)
            got = QCoreApplication.translate("ArcMapSkin", "Zoom In")
            lines.append("%s: load=%s Zoom In -> %r %s" % (lang, ok, got, "OK" if probe is None or got == probe else "MISMATCH"))
            QCoreApplication.removeTranslator(t)
    except Exception:
        lines.append(traceback.format_exc())
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    iface.mainWindow().close()


from qgis.PyQt.QtWidgets import QApplication  # noqa: E402

QTimer.singleShot(4000, run)
