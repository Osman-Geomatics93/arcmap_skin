"""Drive the smoke test from a QGIS started with ``--code tests/run_smoke.py``.

    "C:/Program Files/QGIS 3.44.6/bin/qgis-bin.exe" --profile arcmaptest --code tests/run_smoke.py

Loads and starts the plugin, runs ``smoke_in_qgis.py``, switches the look
off and on once more, writes the result next to this file as
``smoke_result.txt`` (plus every QGIS log message) and quits QGIS.
"""

import contextlib
import io
import os
import traceback

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QApplication

# QGIS runs --code scripts with exec(), so __file__ is not defined there.
HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "smoke_result.txt")
LOG = []


def _log(message, tag, level):
    LOG.append("[%s] %s" % (tag, message))


QgsApplication.messageLog().messageReceived.connect(_log)


def pump(n=30):
    for _ in range(n):
        QApplication.processEvents()


def wait(ms):
    """Let the event loop run (renders, deferred deletes) for ``ms``."""
    from qgis.PyQt.QtCore import QEventLoop

    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


utils_iface_holder = []


def screenshots(iface, plugin, lines):
    """Grab the main window and an attribute table for a visual check."""
    from qgis.core import QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsVectorLayer
    from qgis.PyQt.QtWidgets import QTreeWidget  # noqa: F401

    utils_iface_holder[:] = [iface]

    win = iface.mainWindow()
    win.showNormal()
    win.resize(1500, 950)
    pump(40)
    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string&field=value:int", "Cities", "memory")
    feats = []
    for i, (x, y) in enumerate([(31.2, 30.0), (29.9, 31.2), (32.5, 29.9), (30.8, 31.0)]):
        f = QgsFeature(layer.fields())
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        f.setAttributes(["City %d" % i, i * 10])
        feats.append(f)
    layer.dataProvider().addFeatures(feats)
    poly = QgsVectorLayer("Polygon?crs=EPSG:4326&field=name:string", "Districts", "memory")
    g = QgsGeometry.fromPolygonXY([[QgsPointXY(29.5, 29.5), QgsPointXY(33, 29.5), QgsPointXY(33, 31.5), QgsPointXY(29.5, 31.5)]])
    pf = QgsFeature(poly.fields())
    pf.setGeometry(g)
    pf.setAttributes(["Delta"])
    poly.dataProvider().addFeatures([pf])
    QgsProject.instance().addMapLayers([layer, poly])
    layer.selectByIds([1, 2])
    iface.mapCanvas().zoomToFullExtent()
    wait(2500)
    win.grab().save(os.path.join(HERE, "screenshot_on.png"))
    lines.append("screenshot_on.png written")
    # Query Builder
    from arcmap_skin.query_builder import QueryBuilderDialog

    qb = QueryBuilderDialog(utils_iface_holder[0], QueryBuilderDialog.MODE_SELECT, layer)
    qb.show()
    wait(600)
    qb.fields.setCurrentRow(0)
    qb.load_unique()
    qb.where.setPlainText('"name" LIKE \'City%\'')
    qb.apply()
    lines.append("query builder selected: %d" % layer.selectedFeatureCount())
    wait(300)
    qb.grab().save(os.path.join(HERE, "screenshot_query.png"))
    qb.close()
    # ArcToolbox dock
    from qgis.PyQt.QtWidgets import QDockWidget

    tbx = win.findChild(QDockWidget, "ArcMapToolboxDock")
    if tbx is not None:
        tbx.show()
        tbx.raise_()
        tree = tbx.findChild(QTreeWidget, "ArcMapToolboxTree")
        if tree is not None:
            tree.topLevelItem(0).setExpanded(True)
            tree.topLevelItem(0).child(1).setExpanded(True)
        wait(500)
        tbx.grab().save(os.path.join(HERE, "screenshot_toolbox.png"))
    # Find window
    from arcmap_skin.find import open_find

    fd = open_find(utils_iface_holder[0])
    fd.text.setText("City 1")
    fd.find_features()
    lines.append("find results: %d" % fd.results.rowCount())
    wait(300)
    fd.grab().save(os.path.join(HERE, "screenshot_find.png"))
    fd.close()
    # Getting Started dialog
    from arcmap_skin.getting_started import GettingStartedDialog

    gs = GettingStartedDialog(utils_iface_holder[0])
    gs.show()
    wait(400)
    gs.grab().save(os.path.join(HERE, "screenshot_getting_started.png"))
    gs.close()
    # TOC context menu entries
    from arcmap_skin import toc_menu as tm
    menu_obj = None
    for child in win.findChildren(tm.TocMenu):
        menu_obj = child
    lines.append("toc menu installed: %s" % (menu_obj is not None))
    iface.showAttributeTable(layer)
    wait(800)
    from arcmap_skin import dialogs
    from qgis.PyQt.QtWidgets import QDialog

    candidates = list(QApplication.topLevelWidgets()) + win.findChildren(QDialog)
    lines.append("attribute table candidates: %s" % [w.objectName() for w in candidates if "Attribute" in w.objectName()])
    for w in candidates:
        if w.objectName().startswith("QgsAttributeTableDialog"):
            from qgis.gui import QgsDualView
            from qgis.PyQt.QtWidgets import QToolBar

            lines.append("table toolbars: %s" % [t.objectName() for t in w.findChildren(QToolBar)])
            lines.append("table dual view: %s" % (w.findChild(QgsDualView) is not None))
            lines.append("table layer: %s" % __import__("arcmap_skin.attribute_table", fromlist=["_layer_of"])._layer_of(w))
            lines.append("table done: %s" % w.property(dialogs.TABLE_DONE))
            lines.append("table layout: %s" % type(w.layout()).__name__)
            if not w.property(dialogs.TABLE_DONE):
                dialogs.dress_attribute_table(plugin.changes, w)
            pump(20)
            w.resize(900, 400)
            wait(500)
            w.grab().save(os.path.join(HERE, "screenshot_table.png"))
            lines.append("screenshot_table.png written (%s)" % w.objectName())
            w.close()
            break
    pump(20)


def run():
    lines = []
    try:
        import qgis.utils as utils

        # Start from the ArcMap default layout, not a layout saved by an earlier run.
        from qgis.core import QgsSettings

        QgsSettings().remove("arcmap_skin/skin_state")
        loaded = utils.loadPlugin("arcmap_skin")
        started = utils.startPlugin("arcmap_skin") if loaded else False
        lines.append("loadPlugin=%s startPlugin=%s" % (loaded, started))
        pump()
        plugin = utils.plugins.get("arcmap_skin")
        lines.append("auto-enabled=%s" % (plugin.on if plugin else None))
        # close the Getting Started dialog if it popped up
        from qgis.PyQt.QtWidgets import QDialog

        for w in QApplication.topLevelWidgets():
            if isinstance(w, QDialog) and w.objectName() == "ArcMapGettingStarted":
                w.close()
        buf = io.StringIO()
        with open(os.path.join(HERE, "smoke_in_qgis.py"), encoding="utf-8") as fh:
            smoke_src = fh.read()
        with contextlib.redirect_stdout(buf):
            exec(smoke_src, {"__name__": "__smoke__"})
        lines.append(buf.getvalue().rstrip())
        pump()
        if plugin is not None:
            win = utils.iface.mainWindow()
            from qgis.PyQt.QtWidgets import QToolBar

            tbs = [(tb.objectName(), tb.isVisible()) for tb in win.findChildren(QToolBar) if tb.parent() is win]
            lines.append("toolbars: " + ", ".join("%s=%s" % t for t in tbs))
            lines.append("menubar: " + ", ".join(a.text() for a in win.menuBar().actions()))
            lines.append("changes recorded: %d" % len(plugin.changes))
            screenshots(utils.iface, plugin, lines)
            plugin.disable()
            wait(300)
            lines.append("after disable: changes=%d on=%s" % (len(plugin.changes), plugin.on))
            lines.append("menubar off: " + ", ".join(a.text() for a in win.menuBar().actions()))
            plugin.enable()
            wait(300)
            lines.append("re-enabled: on=%s changes=%d" % (plugin.on, len(plugin.changes)))
            try:
                plugin.unload()  # direct call so a failure shows its traceback here
            except Exception:  # noqa: BLE001
                lines.append("UNLOAD ERROR:" + chr(10) + traceback.format_exc())
            utils.unloadPlugin("arcmap_skin")
            pump()
            lines.append("after unload: menubar: " + ", ".join(a.text() for a in win.menuBar().actions()))
    except Exception:  # noqa: BLE001
        lines.append(traceback.format_exc())
    lines.append("---- QGIS log ----")
    lines.extend(LOG)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    # Close the main window the normal way (close event -> fileExit ->
    # closeProject). QApplication.quit() would skip closeProject and QGIS
    # crashes in its destructor when layers are still loaded. A dirty project
    # would show a "save?" prompt, so mark it clean first.
    from qgis.core import QgsProject
    from qgis.utils import iface

    # Memory layers with features make QGIS ask "close without saving?":
    # drop them so the window can close unattended.
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    from qgis.PyQt.QtWidgets import QDialog

    for w in QApplication.topLevelWidgets():
        if isinstance(w, QDialog) and w.isVisible():
            lines.append("closing dialog before exit: %s %s" % (w.metaObject().className(), w.objectName()))
            w.close()
    with open(OUT, "a", encoding="utf-8") as fh:
        fh.write(chr(10).join(lines[-3:]) + chr(10))
    QTimer.singleShot(1500, dismiss_prompt)
    QTimer.singleShot(4000, report_still_open)
    QTimer.singleShot(300, iface.mainWindow().close)


def dismiss_prompt():
    """Answer any QGIS "save?" prompt with Discard / Close without saving."""
    from qgis.PyQt.QtWidgets import QApplication, QMessageBox

    for w in QApplication.topLevelWidgets():
        if isinstance(w, QMessageBox) and w.isVisible():
            for b in w.buttons():
                if w.buttonRole(b) == QMessageBox.ButtonRole.DestructiveRole or "Discard" in b.text() or "Without" in b.text():
                    b.click()
                    return
            w.reject()


def report_still_open():
    from qgis.PyQt.QtWidgets import QApplication

    tops = [(w.metaObject().className(), w.objectName(), w.windowTitle())
            for w in QApplication.topLevelWidgets() if w.isVisible() and w.isWindow()]
    with open(OUT, "a", encoding="utf-8") as fh:
        fh.write("---- still open after close(): ----" + chr(10) + chr(10).join(map(str, tops)) + chr(10))


QTimer.singleShot(1500, run)
