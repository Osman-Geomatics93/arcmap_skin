# -*- coding: utf-8 -*-
"""ArcMap commands that QGIS has no single action for.

Everything here is a thin wrapper over existing QGIS functionality
(processing algorithms, canvas methods, dock widgets). The actions are
created once per switch-on by :func:`custom_actions` and deleted on undo.
"""

from qgis.core import QgsPointXY, QgsProject
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
)

from .util import arcmap_icon, find_action, find_dock, tr

PROCESSING = {
    "buffer": ("native:buffer", "Buffer…"),
    "clip": ("native:clip", "Clip…"),
    "intersect": ("native:intersection", "Intersect…"),
    "union": ("native:union", "Union…"),
    "merge": ("native:mergevectorlayers", "Merge…"),
    "dissolve": ("native:dissolve", "Dissolve…"),
    "select_by_location": ("native:selectbylocation", "Select By Location…"),
    "spatial_join": ("native:joinattributesbylocation", "Spatial Join…"),
    "erase": ("native:difference", "Erase…"),
}


def _run_algorithm(alg_id):
    try:
        from processing import execAlgorithmDialog
    except ImportError:
        QMessageBox.information(None, tr("ArcMap Skin"), tr("The Processing plugin is not available."))
        return
    execAlgorithmDialog(alg_id, {})


def _show_dock(win, name, focus_child=None):
    dock = find_dock(win, name)
    if dock is None:
        return None
    dock.setVisible(True)
    dock.raise_()
    if focus_child:
        w = dock.findChild(focus_child[0], focus_child[1])
        if w is not None:
            w.setFocus(Qt.FocusReason.OtherFocusReason)
            if hasattr(w, "selectAll"):
                w.selectAll()
    return dock


class GoToXYDialog(QDialog):
    """ArcMap's Go To XY: type a coordinate, centre the map there."""

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.setWindowTitle(tr("Go To XY"))
        form = QFormLayout(self)
        self.x = QLineEdit(self)
        self.y = QLineEdit(self)
        c = iface.mapCanvas().center()
        self.x.setText("%.6f" % c.x())
        self.y.setText("%.6f" % c.y())
        form.addRow(tr("X (Longitude):"), self.x)
        form.addRow(tr("Y (Latitude):"), self.y)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Close)
        buttons.accepted.connect(self.go)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def go(self):
        try:
            x = float(self.x.text().replace(",", "."))
            y = float(self.y.text().replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, tr("Go To XY"), tr("Please enter numeric coordinates."))
            return
        canvas = self.iface.mapCanvas()
        canvas.setCenter(QgsPointXY(x, y))
        canvas.refresh()
        canvas.flashGeometries([_point_geom(x, y)], canvas.mapSettings().destinationCrs())


def _point_geom(x, y):
    from qgis.core import QgsGeometry

    return QgsGeometry.fromPointXY(QgsPointXY(x, y))


def custom_actions(iface, changes):
    """Create the ArcMap-only actions and return them keyed by name."""
    win = iface.mainWindow()
    canvas = iface.mapCanvas()
    acts = {}

    def make(key, text, icon=None, callback=None, checkable=False, tip=None):
        a = QAction(text, win)
        a.setObjectName("ArcMapAction_" + key)
        if icon:
            a.setIcon(arcmap_icon(icon))
        if tip:
            a.setToolTip(tip)
        a.setCheckable(checkable)
        if callback is not None:
            a.triggered.connect(callback)
        acts[key] = a
        return a

    # --- navigation
    make("fixed_zoom_in", tr("Fixed Zoom In"), "fixed_zoom_in", lambda: canvas.zoomIn())
    make("fixed_zoom_out", tr("Fixed Zoom Out"), "fixed_zoom_out", lambda: canvas.zoomOut())
    make("go_to_xy", tr("Go To XY…"), "go_to_xy", lambda: GoToXYDialog(iface).show())

    def find():
        from .find import open_find

        open_find(iface)

    make("find", tr("Find…"), "find", find)

    def add_data():
        """ArcMap's Add Data dialog: one browser tree, pick a dataset."""
        from qgis.core import QgsMapLayer, QgsMeshLayer, QgsProject, QgsRasterLayer, QgsVectorLayer
        from qgis.gui import QgsDataSourceSelectDialog

        dlg = QgsDataSourceSelectDialog(iface.browserModel(), False, QgsMapLayer.LayerType.VectorLayer, win)
        dlg.setWindowTitle(tr("Add Data"))
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        uri = dlg.uri()
        if not uri.isValid():
            return
        kind = uri.layerType
        if kind == "raster":
            layer = QgsRasterLayer(uri.uri, uri.name, uri.providerKey)
        elif kind == "mesh":
            layer = QgsMeshLayer(uri.uri, uri.name, uri.providerKey)
        else:
            layer = QgsVectorLayer(uri.uri, uri.name, uri.providerKey)
        if not layer.isValid():
            # Fall back to QGIS's own handling (e.g. multi-layer sources)
            if not iface.addVectorLayer(uri.uri, uri.name, uri.providerKey):
                iface.messageBar().pushWarning(tr("Add Data"), tr("Could not add %s") % uri.name)
            return
        QgsProject.instance().addMapLayer(layer)

    make("add_data", tr("Add Data…"), "add_data", add_data)

    def connect_folder():
        from qgis.PyQt.QtWidgets import QFileDialog

        folder = QFileDialog.getExistingDirectory(win, tr("Connect To Folder"))
        if folder:
            iface.browserModel().addFavoriteDirectory(folder)
            iface.browserModel().reload()

    make("connect_folder", tr("Connect To Folder…"), "connect_folder", connect_folder)

    def select_by_attributes_dialog():
        from .query_builder import open_select_by_attributes

        open_select_by_attributes(iface)

    def definition_query():
        from .query_builder import open_definition_query

        open_definition_query(iface)

    make("query_builder", tr("Definition Query…"), "select_by_attributes", definition_query)

    def getting_started():
        from .getting_started import show

        show(iface)

    make("getting_started", tr("Getting Started…"), "new_map", getting_started)

    def magnifier():
        from .magnifier import open_magnifier

        open_magnifier(iface)

    make("magnifier", tr("Magnifier"), "zoom_in", magnifier)

    def measure_window():
        from .measure import open_measure

        open_measure(iface)

    make("measure_window", tr("Measure…"), "measure", measure_window)

    def customize():
        from .customize import open_customize

        open_customize(iface, acts)

    make("customize", tr("Customize Mode…"), "customize", customize)
    make("check_geometry", tr("Check Geometry…"), "statistics", lambda: _run_algorithm("native:checkvalidity"))
    make("repair_geometry", tr("Repair Geometry…"), "repair", lambda: _run_algorithm("native:fixgeometries"))

    def skin_options():
        import qgis.utils as utils

        from .settings import show_options_dialog

        show_options_dialog(utils.plugins.get("arcmap_skin"), win)

    make("skin_options", tr("ArcMap Skin Options…"), "options", skin_options)

    # --- views
    def layout_view():
        manager = QgsProject.instance().layoutManager()
        layouts = manager.printLayouts()
        if layouts:
            iface.openLayoutDesigner(layouts[0])
        else:
            a = find_action(win, "mActionNewPrintLayout")
            if a is not None:
                a.trigger()

    make("layout_view", tr("Layout View"), "layout_view", layout_view)
    make("data_view", tr("Data View"), "data_view", lambda: (win.activateWindow(), canvas.setFocus()))

    # --- selection
    make("select_by_attributes", tr("Select By Attributes…"), "select_by_attributes",
         lambda: __import__("arcmap_skin.query_builder", fromlist=["open_select_by_attributes"]).open_select_by_attributes(iface))
    make("clear_selected", tr("Clear Selected Features"), "clear_selected",
         lambda: _trigger(win, "mActionDeselectAll"))

    def selection_statistics():
        _trigger(win, "mActionStatisticalSummary")

    make("statistics", tr("Statistics…"), "statistics", selection_statistics)

    # --- geoprocessing
    for key, (alg, text) in PROCESSING.items():
        make(key, tr(text), key, lambda _=False, alg=alg: _run_algorithm(alg))

    make("arctoolbox", tr("ArcToolbox"), "arctoolbox", lambda: _show_dock(win, "ProcessingToolbox"))
    make("search_tools", tr("Search For Tools"), "search",
         lambda: _show_dock(win, "ProcessingToolbox", (QLineEdit, "searchBox")))
    make("results", tr("Results"), "results", lambda: _trigger(win, "resultsViewer"))
    make("model_builder", tr("ModelBuilder"), "model_builder", lambda: _trigger(win, "modelerAction"))
    make("history", tr("Geoprocessing History"), "history", lambda: _trigger(win, "historyAction"))
    make("environments", tr("Environments…"), "environments", lambda: _trigger(win, "optionsAction"))

    # --- windows
    make("catalog", tr("Catalog"), "catalog", lambda: _show_dock(win, "Browser"))
    make("search", tr("Search"), "search", lambda: _show_dock(win, "ProcessingToolbox", (QLineEdit, "searchBox")))
    make("toc", tr("Table Of Contents"), "toc", lambda: _show_dock(win, "Layers"))

    # --- view toggles wired by mapview / contents_views
    make("status_bar", tr("Status Bar"), None, None, checkable=True)
    acts["status_bar"].setChecked(True)
    make("pause_drawing", tr("Pause Drawing"), "pause_drawing", None, checkable=True)
    make("selectable_layers", tr("Set Selectable Layers…"), "list_by_selection", None)

    # --- layout
    def reset_layout():
        from . import panes, toolbars

        toolbars.reset_toolbars(win)
        panes.reset_panes(win, close_others=True)
        toolbars.hide_replaced_native(win)

    make("reset_layout", tr("Reset ArcMap Layout"), "reset_layout", reset_layout,
         tip=tr("Put toolbars and panes back to the ArcMap default arrangement"))

    # --- about
    def about():
        QMessageBox.about(
            win,
            tr("About ArcMap Skin"),
            tr(
                "<b>ArcMap Skin</b><br>An ArcMap 10 look for QGIS.<br><br>"
                "Not affiliated with, sponsored or endorsed by Esri.<br>"
                "Licensed under GPL-2.0-or-later."
            ),
        )

    make("about", tr("About ArcMap Skin"), "about", about)

    def undo(acts=acts):
        # Close the plugin's floating windows so nothing outlives the plugin.
        from qgis.PyQt.QtWidgets import QApplication

        for w in QApplication.topLevelWidgets():
            if w.objectName() in ("ArcMapMagnifier", "ArcMapMeasure", "ArcMapFindDialog", "ArcMapQueryBuilder",
                                  "ArcMapCustomize", "ArcMapGettingStarted", "ArcMapSkinOptions"):
                w.close()
        for a in acts.values():
            try:
                a.setParent(None)
                a.deleteLater()
            except RuntimeError:
                pass

    changes.add(undo)
    return acts


def _trigger(win, name):
    a = find_action(win, name)
    if a is not None:
        a.trigger()
