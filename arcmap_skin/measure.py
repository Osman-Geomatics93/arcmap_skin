# -*- coding: utf-8 -*-
"""ArcMap's Measure window: Line, Area and Feature measuring with a units
menu and a running total, in one floating window.

Line and Area use QGIS's own measure tools (so snapping and the usual
behaviour apply); Feature is a click-on-feature tool that reports the
length / perimeter and area of the clicked feature. Results are computed
ellipsoidally with QgsDistanceArea in the chosen units.
"""

from qgis.core import Qgis, QgsDistanceArea, QgsProject, QgsUnitTypes, QgsVectorLayer, QgsWkbTypes
from qgis.gui import QgsMapToolIdentifyFeature
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QActionGroup,
    QDialog,
    QMenu,
    QPlainTextEdit,
    QToolBar,
    QToolButton,
    QVBoxLayout,
)

from .util import alive, arcmap_icon, find_action, tr

DISTANCE_UNITS = [
    ("Meters", Qgis.DistanceUnit.Meters),
    ("Kilometers", Qgis.DistanceUnit.Kilometers),
    ("Feet", Qgis.DistanceUnit.Feet),
    ("Yards", Qgis.DistanceUnit.Yards),
    ("Miles", Qgis.DistanceUnit.Miles),
    ("Nautical Miles", Qgis.DistanceUnit.NauticalMiles),
]
AREA_UNITS = [
    ("Square Meters", Qgis.AreaUnit.SquareMeters),
    ("Hectares", Qgis.AreaUnit.Hectares),
    ("Square Kilometers", Qgis.AreaUnit.SquareKilometers),
    ("Acres", Qgis.AreaUnit.Acres),
    ("Square Feet", Qgis.AreaUnit.SquareFeet),
    ("Square Miles", Qgis.AreaUnit.SquareMiles),
]


class FeatureMeasureTool(QgsMapToolIdentifyFeature):
    def __init__(self, canvas, window):
        super().__init__(canvas)
        self.window = window
        self.featureIdentified.connect(self._identified)

    def _identified(self, feature):
        self.window.report_feature(feature, self.layer())


class MeasureWindow(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow(), Qt.WindowType.Tool)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.win = iface.mainWindow()
        self.setObjectName("ArcMapMeasure")
        self.setWindowTitle(tr("Measure"))
        self.setWindowIcon(arcmap_icon("measure"))
        self.resize(360, 260)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        bar = QToolBar(self)
        bar.setIconSize(self.win.iconSize())
        self.line = find_action(self.win, "mActionMeasure")
        self.area = find_action(self.win, "mActionMeasureArea")
        if self.line is not None:
            bar.addAction(self.line)
        if self.area is not None:
            bar.addAction(self.area)
        self.feature_button = QToolButton(bar)
        self.feature_button.setIcon(arcmap_icon("identify"))
        self.feature_button.setToolTip(tr("Measure a Feature"))
        self.feature_button.setCheckable(True)
        self.feature_button.clicked.connect(self._feature_mode)
        bar.addWidget(self.feature_button)
        bar.addSeparator()
        clear = bar.addAction(arcmap_icon("clear_selected"), tr("Clear and Reset Results"))
        clear.triggered.connect(self.clear)
        bar.addSeparator()
        self.units_button = QToolButton(bar)
        self.units_button.setText(tr("Choose Units"))
        self.units_button.setIcon(arcmap_icon("go_to_xy"))
        self.units_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.units_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(self.units_button)
        dist = menu.addMenu(tr("Distance"))
        self.dist_group = QActionGroup(dist)
        for text, unit in DISTANCE_UNITS:
            a = dist.addAction(tr(text))
            a.setCheckable(True)
            a.setData(int(unit))
            self.dist_group.addAction(a)
        self.dist_group.actions()[0].setChecked(True)
        area = menu.addMenu(tr("Area"))
        self.area_group = QActionGroup(area)
        for text, unit in AREA_UNITS:
            a = area.addAction(tr(text))
            a.setCheckable(True)
            a.setData(int(unit))
            self.area_group.addAction(a)
        self.area_group.actions()[0].setChecked(True)
        self.units_button.setMenu(menu)
        bar.addWidget(self.units_button)
        layout.addWidget(bar)
        self.results = QPlainTextEdit(self)
        self.results.setReadOnly(True)
        self.results.setPlaceholderText(tr("Measure Line and Measure Area use the QGIS measure dialog; "
                                           "Measure a Feature reports the clicked feature here."))
        layout.addWidget(self.results, 1)
        self.tool = FeatureMeasureTool(self.canvas, self)
        self.canvas.mapToolSet.connect(self._tool_changed)
        self.total_length = 0.0
        self.total_area = 0.0

    # ------------------------------------------------------------ helpers

    def _distance_unit(self):
        a = self.dist_group.checkedAction()
        return Qgis.DistanceUnit(a.data()) if a else Qgis.DistanceUnit.Meters

    def _area_unit(self):
        a = self.area_group.checkedAction()
        return Qgis.AreaUnit(a.data()) if a else Qgis.AreaUnit.SquareMeters

    def _feature_mode(self, on):
        if on:
            self.tool_used = True
            self.canvas.setMapTool(self.tool)
        else:
            self._release_tool()

    def _release_tool(self):
        """Never leave the canvas pointing at our tool (also as last tool)."""
        if not alive(self.canvas):
            return
        if self.canvas.mapTool() is self.tool:
            self.canvas.unsetMapTool(self.tool)
        if getattr(self, "tool_used", False):
            pan = self.iface.actionPan()
            if pan is not None:
                pan.trigger()
            self.tool_used = False

    def _tool_changed(self, tool, old=None):
        self.feature_button.setChecked(tool is self.tool)

    def clear(self):
        self.results.clear()
        self.total_length = 0.0
        self.total_area = 0.0

    def report_feature(self, feature, layer):
        if not isinstance(layer, QgsVectorLayer):
            return
        da = QgsDistanceArea()
        da.setSourceCrs(layer.crs(), QgsProject.instance().transformContext())
        da.setEllipsoid(QgsProject.instance().ellipsoid())
        geom = feature.geometry()
        du, au = self._distance_unit(), self._area_unit()
        lines = ["%s – %s %s" % (layer.name(), tr("feature"), feature.id())]
        gtype = QgsWkbTypes.geometryType(geom.wkbType())
        if gtype == Qgis.GeometryType.Polygon:
            area = da.convertAreaMeasurement(da.measureArea(geom), au)
            perim = da.convertLengthMeasurement(da.measurePerimeter(geom), du)
            self.total_area += area
            lines.append(tr("Area: %s %s") % (_fmt(area), QgsUnitTypes.toString(au)))
            lines.append(tr("Perimeter: %s %s") % (_fmt(perim), QgsUnitTypes.toString(du)))
            lines.append(tr("Running total area: %s %s") % (_fmt(self.total_area), QgsUnitTypes.toString(au)))
        elif gtype == Qgis.GeometryType.Line:
            length = da.convertLengthMeasurement(da.measureLength(geom), du)
            self.total_length += length
            lines.append(tr("Length: %s %s") % (_fmt(length), QgsUnitTypes.toString(du)))
            lines.append(tr("Running total length: %s %s") % (_fmt(self.total_length), QgsUnitTypes.toString(du)))
        else:
            pt = geom.asPoint() if not geom.isMultipart() else geom.centroid().asPoint()
            lines.append("X: %.6f  Y: %.6f" % (pt.x(), pt.y()))
        self.results.appendPlainText("\n".join(lines) + "\n")

    def closeEvent(self, event):  # noqa: N802
        if alive(self.canvas):
            try:
                self.canvas.mapToolSet.disconnect(self._tool_changed)
            except (TypeError, RuntimeError):
                pass
        self._release_tool()
        super().closeEvent(event)


def _fmt(value):
    return ("%.3f" % value).rstrip("0").rstrip(".") if value < 1e6 else "%.0f" % value


_window = None


def open_measure(iface):
    global _window
    if _window is None or not alive(_window) or not _window.isVisible():
        _window = MeasureWindow(iface)
        _window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    _window.show()
    _window.raise_()
    return _window
