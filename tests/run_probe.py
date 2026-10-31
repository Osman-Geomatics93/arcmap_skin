"""Probe why the plugin did not auto-load: writes probe_result.txt and closes."""

import os
import traceback

from qgis.PyQt.QtCore import QEventLoop, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def run():
    import qgis.utils as utils
    from qgis.core import QgsApplication, QgsProject, QgsSettings

    lines = []
    wait(2000)
    try:
        lines.append("available: %s" % sorted(utils.available_plugins))
        lines.append("active: %s" % sorted(utils.active_plugins))
        lines.append("setting PythonPlugins/arcmap_skin = %r" % QgsSettings().value("PythonPlugins/arcmap_skin"))
        lines.append("plugin_paths: %s" % utils.plugin_paths)
        lines.append("profile: %s" % QgsApplication.qgisSettingsDirPath())
        lines.append("UI/UITheme: %r" % QgsSettings().value("UI/UITheme"))
        if "arcmap_skin" in utils.available_plugins and "arcmap_skin" not in utils.active_plugins:
            ok = utils.loadPlugin("arcmap_skin")
            lines.append("manual loadPlugin -> %s" % ok)
            if ok:
                lines.append("manual startPlugin -> %s" % utils.startPlugin("arcmap_skin"))
    except Exception:
        lines.append(traceback.format_exc())
    with open(os.path.join(HERE, "probe_result.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().setDirty(False)
    utils.iface.mainWindow().close()


QTimer.singleShot(500, run)
