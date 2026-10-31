"""Startup check: ``qgis-bin.exe --code tests/run_startup.py`` (any profile).

Does not load the plugin itself: it relies on QGIS auto-loading it. Waits
for the look to switch on (up to 15 s), writes screenshot_startup.png and
startup_result.txt (with the plugin's log) next to this file, then closes
QGIS normally, answering a "save project?" prompt with Discard.
"""

import os

from qgis.PyQt.QtCore import QEventLoop, QTimer

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "D:/QGIS_Plugins/Arcmap_Skin/tests"
LOG = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def _log(message, tag, level):
    LOG.append("[%s] %s" % (tag, message))


def dismiss_save_prompt():
    """If QGIS asks to save the project, answer Discard so the test can end."""
    from qgis.PyQt.QtWidgets import QApplication, QMessageBox

    for w in QApplication.topLevelWidgets():
        if isinstance(w, QMessageBox) and w.isVisible():
            for b in w.buttons():
                role = w.buttonRole(b)
                if role == QMessageBox.ButtonRole.DestructiveRole or "Discard" in b.text() or "Don't Save" in b.text():
                    b.click()
                    return
            w.reject()


def run():
    import qgis.utils as utils
    from qgis.core import QgsApplication, QgsProject
    from qgis.PyQt.QtWidgets import QToolBar

    QgsApplication.messageLog().messageReceived.connect(_log)
    plugin = None
    for _ in range(240):  # up to 120 s for the look to switch on
        wait(500)
        plugin = utils.plugins.get("arcmap_skin")
        if plugin is not None and plugin.on:
            break
    win = utils.iface.mainWindow()
    win.showNormal()
    win.resize(1500, 950)
    wait(2000)
    win.grab().save(os.path.join(HERE, "screenshot_startup.png"))
    tbs = [tb.objectName() for tb in win.findChildren(QToolBar) if tb.parent() is win and tb.isVisible()]
    with open(os.path.join(HERE, "startup_result.txt"), "w", encoding="utf-8") as fh:
        fh.write("profile: %s\n" % QgsApplication.qgisSettingsDirPath())
        fh.write("plugin loaded=%s on=%s\n" % (plugin is not None, getattr(plugin, "on", None)))
        fh.write("project dirty=%s\n" % QgsProject.instance().isDirty())
        fh.write("visible toolbars: %s\n" % ", ".join(tbs))
        fh.write("menubar: %s\n" % ", ".join(a.text() for a in win.menuBar().actions()))
        fh.write("---- log ----\n" + "\n".join(LOG) + "\n")
    from qgis.PyQt.QtWidgets import QApplication, QDialog

    for w in QApplication.topLevelWidgets():
        if isinstance(w, QDialog) and w.isVisible():
            w.reject()
    wait(300)
    QgsProject.instance().setDirty(False)
    QTimer.singleShot(1500, dismiss_save_prompt)
    QTimer.singleShot(4000, report_still_open)
    win.close()


def report_still_open():
    """If QGIS did not close, record which windows are up."""
    from qgis.PyQt.QtWidgets import QApplication

    tops = [(w.metaObject().className(), w.objectName(), w.windowTitle())
            for w in QApplication.topLevelWidgets() if w.isVisible() and w.isWindow()]
    with open(os.path.join(HERE, "startup_result.txt"), "a", encoding="utf-8") as fh:
        fh.write("---- still open after close(): ----\n%s\n" % "\n".join(map(str, tops)))


QTimer.singleShot(500, run)
