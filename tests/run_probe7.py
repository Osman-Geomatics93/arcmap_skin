"""Check the ArcMap layer-properties tabs; screenshot_props.png + probe7_result.txt."""

import os

from qgis.PyQt.QtCore import QEventLoop, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe7_result.txt")
lines = []


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def inspect():
    from qgis.PyQt.QtWidgets import QApplication, QListWidget, QStackedWidget, QTabBar

    w = QApplication.activeModalWidget()
    lines.append("modal: %s" % (w.metaObject().className() if w else None))
    if w is None:
        return
    import qgis.utils as utils
    from arcmap_skin import dialogs

    plugin = utils.plugins.get("arcmap_skin")
    dialogs.dress_layer_properties(plugin.changes, w, utils.iface)
    dialogs.dress_renderer_combos(w)
    wait(300)
    bar = w.findChild(QTabBar, "ArcMapPropertyTabBar")
    lw = w.findChild(QListWidget, "mOptionsListWidget")
    stack = w.findChild(QStackedWidget, "mOptionsStackedWidget")
    lines.append("tabs: %s" % ([bar.tabText(i) for i in range(bar.count())] if bar else None))
    lines.append("list visible: %s" % lw.parent().isVisible())
    for i in range(bar.count() - 1):
        bar.setCurrentIndex(i)
        wait(100)
        lines.append("  tab %r -> page %r (list row %d)" % (bar.tabText(i), stack.currentWidget().objectName(), lw.currentRow()))
    bar.setCurrentIndex(3)  # Symbology
    wait(400)
    w.resize(900, 620)
    wait(300)
    w.grab().save(os.path.join(HERE, "screenshot_props.png"))
    # More menu entries
    tabs_widget = w.findChild(QTabBar, "ArcMapPropertyTabBar").parent()
    lines.append("more: %s" % [a.text() for a in tabs_widget.more_menu.actions()])
    w.reject()


def run():
    import qgis.utils as utils
    from qgis.core import QgsProject, QgsVectorLayer

    iface = utils.iface
    utils.loadPlugin("arcmap_skin")
    utils.startPlugin("arcmap_skin")
    plugin = utils.plugins.get("arcmap_skin")
    for _ in range(40):
        wait(500)
        if plugin.on:
            break
    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string", "Cities", "memory")
    QgsProject.instance().addMapLayer(layer)
    QTimer.singleShot(2500, inspect)
    iface.showLayerProperties(layer)
    wait(500)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().removeAllMapLayers()
    QgsProject.instance().setDirty(False)
    iface.mainWindow().close()


QTimer.singleShot(1500, run)
