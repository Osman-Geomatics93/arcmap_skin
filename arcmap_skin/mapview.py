# -*- coding: utf-8 -*-
"""The ArcMap map frame: Data View / Layout View buttons under the map and
an ArcMap-style status bar (message on the left, coordinates and units on
the right). The QGIS status bar is hidden while the look is on.

Both widgets are rows appended to the central widget's grid layout, so
they never fight with the QGIS message bar, which shares the top cell with
the map. Canvas signals are connected to bound methods, not lambdas, so
PyQt disconnects them automatically when the widgets are deleted.
"""

import math

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsSettings,
    QgsUnitTypes,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QActionGroup
from qgis.PyQt.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QProgressBar,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from .util import SETTINGS_GROUP, alive, arcmap_icon, tool_button, tr

UNIT_KEY = SETTINGS_GROUP + "/coordinate_format"
UNIT_FORMATS = [
    ("map", "Map Units"),
    ("dd", "Decimal Degrees"),
    ("dms", "Degrees Minutes Seconds"),
    ("ddm", "Degrees Decimal Minutes"),
]

UNIT_NAMES = {
    Qgis.DistanceUnit.Meters: "Meters",
    Qgis.DistanceUnit.Kilometers: "Kilometers",
    Qgis.DistanceUnit.Feet: "Feet",
    Qgis.DistanceUnit.NauticalMiles: "Nautical Miles",
    Qgis.DistanceUnit.Yards: "Yards",
    Qgis.DistanceUnit.Miles: "Miles",
    Qgis.DistanceUnit.Degrees: "Decimal Degrees",
    Qgis.DistanceUnit.Centimeters: "Centimeters",
    Qgis.DistanceUnit.Millimeters: "Millimeters",
    Qgis.DistanceUnit.Unknown: "Unknown Units",
}


class ViewButtons(QWidget):
    """ArcMap's two small view buttons at the bottom-left of the map."""

    def __init__(self, iface, actions, parent):
        super().__init__(parent)
        self.setObjectName("ArcMapViewButtons")
        self.iface = iface
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 0, 0)
        layout.setSpacing(0)
        self.data = QToolButton(self)
        self.data.setObjectName("ArcMapDataViewButton")
        self.data.setIcon(arcmap_icon("data_view"))
        self.data.setToolTip(tr("Data View"))
        self.data.setCheckable(True)
        self.data.setChecked(True)
        self.data.setAutoExclusive(True)
        self.layout_btn = QToolButton(self)
        self.layout_btn.setObjectName("ArcMapLayoutViewButton")
        self.layout_btn.setIcon(arcmap_icon("layout_view"))
        self.layout_btn.setToolTip(tr("Layout View"))
        self.layout_btn.setCheckable(True)
        self.layout_btn.setAutoExclusive(True)
        for b in (self.data, self.layout_btn):
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            layout.addWidget(b)
        layout.addStretch(1)
        self.setFixedHeight(20)
        self.layout_btn.clicked.connect(self._layout)
        self.data.clicked.connect(self._data)
        self._actions = actions

    def _layout(self):
        action = self._actions.get("layout_view")
        if action is not None:
            action.trigger()
        # The layout opens in its own window; the map keeps showing data.
        QTimer.singleShot(400, self._back_to_data)

    def _back_to_data(self):
        if alive(self):
            self.data.setChecked(True)

    def _data(self):
        action = self._actions.get("data_view")
        if action is not None:
            action.trigger()

    def remove(self):
        self.hide()
        self.setParent(None)
        self.deleteLater()


class StatusFooter(QWidget):
    """ArcMap status bar: message area left, coordinate readout right."""

    def __init__(self, iface, actions, parent):
        super().__init__(parent)
        self.setObjectName("ArcMapStatusBar")
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.win = iface.mainWindow()
        self._typing = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        self.message = QLabel("", self)
        self.message.setObjectName("ArcMapStatusMessage")
        self.message.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.message, 1)

        # Drawing… indicator and task progress (ArcMap shows these bottom-left)
        self.drawing = QLabel("", self)
        self.drawing.setObjectName("ArcMapDrawingLabel")
        layout.addWidget(self.drawing)
        self.progress = QProgressBar(self)
        self.progress.setObjectName("ArcMapTaskProgress")
        self.progress.setRange(0, 100)
        self.progress.setFixedWidth(140)
        self.progress.setTextVisible(True)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.tasks_button = QToolButton(self)
        self.tasks_button.setObjectName("ArcMapTasksButton")
        self.tasks_button.setAutoRaise(True)
        self.tasks_button.setIcon(arcmap_icon("history"))
        self.tasks_button.setToolTip(tr("Running tasks"))
        self.tasks_button.clicked.connect(self._show_tasks)
        self.tasks_button.hide()
        layout.addWidget(self.tasks_button)

        self.selection = QLabel("", self)
        self.selection.setObjectName("ArcMapSelectionCount")
        layout.addWidget(self.selection)

        self.pause = tool_button(arcmap_icon("pause_drawing"), tr("Pause Drawing"), checkable=True, size=16, parent=self)
        self.pause.setObjectName("ArcMapPauseDrawing")
        self.pause.toggled.connect(self._pause_toggled)
        layout.addWidget(self.pause)
        self._pause_action = actions.get("pause_drawing")
        if self._pause_action is not None:
            self._pause_action.toggled.connect(self.pause.setChecked)
            self.pause.toggled.connect(self._pause_action.setChecked)

        self.crs = QToolButton(self)
        self.crs.setObjectName("ArcMapCrsButton")
        self.crs.setAutoRaise(True)
        self.crs.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.crs.setIcon(arcmap_icon("crs"))
        self.crs.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.crs.clicked.connect(self._crs_dialog)
        layout.addWidget(self.crs)

        self.coords = QLabel("", self)
        self.coords.setObjectName("ArcMapCoords")
        self.coords.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.coords.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.coords)

        # Display units menu (ArcMap: Data Frame Properties > Display units)
        self.units_button = QToolButton(self)
        self.units_button.setObjectName("ArcMapUnitsButton")
        self.units_button.setAutoRaise(True)
        self.units_button.setToolTip(tr("Display units"))
        self.units_button.setIcon(arcmap_icon("go_to_xy"))
        self.units_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.units_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.units_menu = QMenu(self.units_button)
        self.units_group = QActionGroup(self.units_menu)
        self.units_group.setExclusive(True)
        self.unit_format = QgsSettings().value(UNIT_KEY, "map", type=str)
        for key, text in UNIT_FORMATS:
            a = self.units_menu.addAction(tr(text))
            a.setCheckable(True)
            a.setData(key)
            a.setChecked(key == self.unit_format)
            self.units_group.addAction(a)
        self.units_group.triggered.connect(self._units_changed)
        self.units_button.setMenu(self.units_menu)
        layout.addWidget(self.units_button)
        self._last_point = None
        self.setFixedHeight(24)

        # QGIS status messages (tool hints etc.) show on the left.
        bar = self.win.statusBar()
        if bar is not None:
            bar.messageChanged.connect(self.message.setText)
        self.canvas.renderStarting.connect(self._render_started)
        self.canvas.mapCanvasRefreshed.connect(self._render_done)
        manager = QgsApplication.taskManager()
        manager.progressChanged.connect(self._task_progress)
        manager.countActiveTasksChanged.connect(self._task_count)
        # QGIS's own status-bar progress bar (used by some loaders) is mirrored
        qgis_bar = self.win.statusBar().findChild(QProgressBar, "mProgressBar") if self.win.statusBar() else None
        self._qgis_bar = qgis_bar
        if qgis_bar is not None:
            qgis_bar.valueChanged.connect(self._qgis_progress)
        self.canvas.xyCoordinates.connect(self.show_coordinates)
        self.canvas.destinationCrsChanged.connect(self.show_crs)
        self.canvas.selectionChanged.connect(self.count_selection)
        self.canvas.layersChanged.connect(self.count_selection)
        QgsProject.instance().layersRemoved.connect(self.count_selection)
        self.show_crs()
        self.count_selection()
        self.show_coordinates(self.canvas.center())

        status_action = actions.get("status_bar")
        if status_action is not None:
            status_action.setChecked(True)
            status_action.toggled.connect(self.setVisible)

    # ------------------------------------------------------------- updates

    def _units_changed(self, action):
        self.unit_format = action.data()
        QgsSettings().setValue(UNIT_KEY, self.unit_format)
        if self._last_point is not None:
            self.show_coordinates(self._last_point)

    def _to_geographic(self, point):
        crs = self.canvas.mapSettings().destinationCrs()
        if crs.isGeographic():
            return point
        try:
            xform = QgsCoordinateTransform(crs, QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())
            return xform.transform(point)
        except Exception:  # noqa: BLE001
            return None

    def show_coordinates(self, point):
        self._last_point = point
        crs = self.canvas.mapSettings().destinationCrs()
        units = self.canvas.mapUnits()
        fmt_key = self.unit_format
        if fmt_key in ("dd", "dms", "ddm"):
            geo = self._to_geographic(point)
            if geo is None:
                self.coords.setText(chr(8212))
                return
            if fmt_key == "dd":
                self.coords.setText("%.6f  %.6f  %s" % (geo.x(), geo.y(), tr("Decimal Degrees")))
            elif fmt_key == "dms":
                self.coords.setText("%s  %s" % (_dms(geo.x(), "EW"), _dms(geo.y(), "NS")))
            else:
                self.coords.setText("%s  %s" % (_ddm(geo.x(), "EW"), _ddm(geo.y(), "NS")))
            return
        precision = _precision(self.canvas.mapUnitsPerPixel(), crs)
        fmt = "%%.%df  %%.%df  %%s" % (precision, precision)
        name = UNIT_NAMES.get(units, QgsUnitTypes.toString(units).title())
        self.coords.setText(fmt % (point.x(), point.y(), tr(name)))

    def show_crs(self):
        crs = self.canvas.mapSettings().destinationCrs()
        self.crs.setText(crs.authid() if crs.isValid() else tr("No CRS"))
        self.crs.setToolTip(crs.description() if crs.isValid() else tr("No coordinate reference system"))

    def count_selection(self, *_):
        total = 0
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                total += layer.selectedFeatureCount()
        self.selection.setText(tr("%d selected") % total if total else "")

    def _render_started(self):
        self.drawing.setText(tr("Drawing…"))

    def _render_done(self):
        self.drawing.setText("")

    def _task_progress(self, task_id, progress):
        manager = QgsApplication.taskManager()
        task = manager.task(task_id)
        if task is not None:
            self.progress.setFormat("%s %d%%" % (task.description()[:28], int(progress)))
        self.progress.setValue(int(progress))
        self.progress.show()

    def _task_count(self, count):
        self.tasks_button.setVisible(count > 0)
        if count <= 0:
            self.progress.hide()
            self.progress.setValue(0)

    def _qgis_progress(self, value):
        bar = self._qgis_bar
        if bar is None or not alive(bar):
            return
        if bar.maximum() > 0 and 0 < value < bar.maximum():
            self.progress.setRange(0, bar.maximum())
            self.progress.setFormat(tr("Loading… %p%"))
            self.progress.setValue(value)
            self.progress.show()
        elif value >= bar.maximum() or value <= 0:
            if QgsApplication.taskManager().countActiveTasks() == 0:
                self.progress.hide()
            self.progress.setRange(0, 100)

    def _show_tasks(self):
        from qgis.gui import QgsTaskManagerWidget
        from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout

        dlg = QDialog(self.win)
        dlg.setWindowTitle(tr("Running tasks"))
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        lay = QVBoxLayout(dlg)
        lay.addWidget(QgsTaskManagerWidget(QgsApplication.taskManager(), dlg))
        dlg.resize(420, 240)
        dlg.show()

    def _pause_toggled(self, on):
        if alive(self.canvas):
            self.canvas.setRenderFlag(not on)

    def _crs_dialog(self):
        button = self.win.findChild(QToolButton, "mOntheFlyProjectionStatusButton")
        if button is not None:
            button.click()
        else:
            self.iface.showProjectPropertiesDialog("CRS")

    # -------------------------------------------------------------- removal

    def remove(self):
        if alive(self.canvas) and self.pause.isChecked():
            self.canvas.setRenderFlag(True)
        manager = QgsApplication.taskManager()
        for signal, slot in ((manager.progressChanged, self._task_progress), (manager.countActiveTasksChanged, self._task_count)):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        if self._qgis_bar is not None and alive(self._qgis_bar):
            try:
                self._qgis_bar.valueChanged.disconnect(self._qgis_progress)
            except (TypeError, RuntimeError):
                pass
        bar = self.win.statusBar() if alive(self.win) else None
        if bar is not None:
            try:
                bar.messageChanged.disconnect(self.message.setText)
            except (TypeError, RuntimeError):
                pass
        self.hide()
        self.setParent(None)
        self.deleteLater()


DEG = chr(176)


def _dms(value, hemispheres):
    hemi = hemispheres[0] if value >= 0 else hemispheres[1]
    value = abs(value)
    d = int(value)
    m = int((value - d) * 60)
    s = (value - d - m / 60.0) * 3600
    return "%d%s%02d'%05.2f\"%s" % (d, DEG, m, s, hemi)


def _ddm(value, hemispheres):
    hemi = hemispheres[0] if value >= 0 else hemispheres[1]
    value = abs(value)
    d = int(value)
    m = (value - d) * 60
    return "%d%s%07.4f'%s" % (d, DEG, m, hemi)


def _precision(map_units_per_pixel, crs):
    """Decimals so that the readout changes with every pixel (as QGIS does)."""
    if map_units_per_pixel <= 0:
        return 6 if crs.isGeographic() else 2
    digits = int(math.ceil(-math.log10(map_units_per_pixel))) if map_units_per_pixel < 1 else 0
    return max(0, min(digits, 10))


def _central_grid(win):
    central = win.centralWidget()
    if central is None:
        return None
    layout = central.layout()
    return layout if isinstance(layout, QGridLayout) else None


def frame_map(iface, changes, actions):
    win = iface.mainWindow()
    grid = _central_grid(win)
    if grid is None:
        return None
    columns = max(1, grid.columnCount())
    buttons = ViewButtons(iface, actions, win.centralWidget())
    grid.addWidget(buttons, grid.rowCount(), 0, 1, columns)
    footer = StatusFooter(iface, actions, win.centralWidget())
    grid.addWidget(footer, grid.rowCount(), 0, 1, columns)

    def undo(grid=grid, buttons=buttons, footer=footer):
        for w in (footer, buttons):
            if alive(w):
                if alive(grid):
                    grid.removeWidget(w)
                w.remove()

    changes.add(undo)
    changes.set(win.statusBar(), "visible", False)
    return footer
