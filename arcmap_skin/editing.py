# -*- coding: utf-8 -*-
"""ArcMap editing workflow: Start/Stop Editing, the Create Features window
and an ArcMap-style Snapping toolbar.

* ``start_editing``: with no editable layer chosen, asks which layer to
  edit (ArcMap's Start Editing dialog), then toggles editing on it.
* ``stop_editing``: asks "Do you want to save your edits?" and commits or
  rolls back.
* :class:`CreateFeaturesDock`: layers being edited, one row per layer
  (ArcMap's feature templates), plus construction tools underneath.
* :class:`SnappingToolBar`: Point / End / Vertex / Edge / Midpoint /
  Intersection toggles bound to the project snapping configuration.
"""

from qgis.core import Qgis, QgsProject, QgsSnappingConfig, QgsVectorLayer, QgsWkbTypes
from qgis.PyQt.QtCore import QSize, Qt, QTimer
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .util import alive, arcmap_icon, find_action, tool_button, tr

LAYER_ROLE = Qt.ItemDataRole.UserRole + 7


def _editable_layers():
    out = []
    for layer in QgsProject.instance().mapLayers().values():
        if isinstance(layer, QgsVectorLayer) and layer.isSpatial() and not layer.readOnly():
            caps = layer.dataProvider().capabilities() if layer.dataProvider() else 0
            if caps & layer.dataProvider().ChangeGeometries or caps & layer.dataProvider().AddFeatures:
                out.append(layer)
    return out


class StartEditingDialog(QDialog):
    def __init__(self, iface, layers):
        super().__init__(iface.mainWindow())
        self.setWindowTitle(tr("Start Editing"))
        self.resize(420, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("Select the layer or workspace to edit:"), self))
        self.list = QListWidget(self)
        for layer in layers:
            item = QListWidgetItem(layer.name())
            item.setData(LAYER_ROLE, layer.id())
            item.setToolTip(layer.source())
            self.list.addItem(item)
        layout.addWidget(self.list, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.list.itemDoubleClicked.connect(lambda *_: self.accept())
        if self.list.count():
            self.list.setCurrentRow(0)

    def layer(self):
        item = self.list.currentItem()
        return QgsProject.instance().mapLayer(item.data(LAYER_ROLE)) if item else None


def start_editing(iface, layer=None):
    if layer is None:
        layer = iface.activeLayer()
    layers = _editable_layers()
    if not isinstance(layer, QgsVectorLayer) or layer not in layers:
        if not layers:
            QMessageBox.information(iface.mainWindow(), tr("Start Editing"), tr("There are no editable layers in the map."))
            return
        dlg = StartEditingDialog(iface, layers)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        layer = dlg.layer()
        if layer is None:
            return
    if not layer.isEditable():
        layer.startEditing()
    iface.setActiveLayer(layer)
    return layer


def stop_editing(iface, layer=None, save=None):
    if layer is None:
        layer = iface.activeLayer()
    if not isinstance(layer, QgsVectorLayer) or not layer.isEditable():
        # Stop all editing sessions
        layers = [lyr for lyr in QgsProject.instance().mapLayers().values()
                  if isinstance(lyr, QgsVectorLayer) and lyr.isEditable()]
        if not layers:
            return
    else:
        layers = [layer]
    for lyr in layers:
        choice = save
        if choice is None and lyr.isModified():
            answer = QMessageBox.question(
                iface.mainWindow(),
                tr("Save"),
                tr("Do you want to save your edits to %s?") % lyr.name(),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                return
            choice = answer == QMessageBox.StandardButton.Yes
        if choice:
            if not lyr.commitChanges():
                QMessageBox.warning(iface.mainWindow(), tr("Save Edits"), "\n".join(lyr.commitErrors()))
                continue
            if save is True:
                lyr.startEditing()  # "Save Edits" keeps the session open
        else:
            lyr.rollBack()
        lyr.triggerRepaint()


# ------------------------------------------------------------ create features


class CreateFeaturesDock(QDockWidget):
    CONSTRUCTION = [
        ("mActionAddFeature", "sketch", "Point / Line / Polygon"),
        ("mActionDigitizeWithSegment", "sketch", "Straight Segment"),
        ("mActionDigitizeWithCurve", "reshape", "Arc Segment"),
        ("mActionStreamDigitize", "edit_tool", "Freehand"),
        ("mActionDigitizeShape", "select_polygon", "Shape"),
        ("EnableTracingAction", "hyperlink", "Trace"),
    ]

    def __init__(self, iface):
        super().__init__(tr("Create Features"), iface.mainWindow())
        self.iface = iface
        self.win = iface.mainWindow()
        self.setObjectName("ArcMapCreateFeaturesDock")
        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        self.templates = QListWidget(body)
        self.templates.setObjectName("ArcMapFeatureTemplates")
        self.templates.setIconSize(QSize(16, 16))
        layout.addWidget(self.templates, 1)
        self.hint = QLabel(tr("Start editing a layer to see its feature templates."), body)
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        layout.addWidget(QLabel(tr("Construction Tools"), body))
        tools = QToolBar(body)
        tools.setIconSize(QSize(18, 18))
        tools.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        tools.setOrientation(Qt.Orientation.Vertical)
        for name, icon, caption in self.CONSTRUCTION:
            action = find_action(self.win, name)
            if action is None:
                continue
            btn = QToolButton(tools)
            btn.setDefaultAction(action)
            btn.setIcon(action.icon() if not action.icon().isNull() else arcmap_icon(icon))
            btn.setText(tr(caption))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            btn.setAutoRaise(True)
            tools.addWidget(btn)
        layout.addWidget(tools)
        self.setWidget(body)
        self.templates.itemClicked.connect(self._pick)
        project = QgsProject.instance()
        project.layersAdded.connect(self.refresh)
        project.layersRemoved.connect(self.refresh)
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def _layer_icon(self, layer):
        from qgis.core import QgsSymbolLayerUtils

        renderer = layer.renderer()
        if renderer is not None:
            symbols = renderer.symbols(__import__("qgis.core", fromlist=["QgsRenderContext"]).QgsRenderContext())
            if symbols:
                return QgsSymbolLayerUtils.symbolPreviewIcon(symbols[0], QSize(16, 16))
        return arcmap_icon("new_layer")

    def refresh(self, *_):
        if not self.isVisible():
            return
        current = self.templates.currentItem().data(LAYER_ROLE) if self.templates.currentItem() else None
        self.templates.blockSignals(True)
        self.templates.clear()
        editing = [lyr for lyr in QgsProject.instance().mapLayers().values()
                   if isinstance(lyr, QgsVectorLayer) and lyr.isEditable()]
        for layer in editing:
            item = QListWidgetItem(self._layer_icon(layer), layer.name())
            item.setData(LAYER_ROLE, layer.id())
            kind = QgsWkbTypes.displayString(layer.wkbType())
            item.setToolTip(tr("%s – click to create new %s features") % (layer.name(), kind))
            self.templates.addItem(item)
            if layer.id() == current:
                self.templates.setCurrentItem(item)
        self.templates.blockSignals(False)
        self.hint.setVisible(not editing)

    def _pick(self, item):
        layer = QgsProject.instance().mapLayer(item.data(LAYER_ROLE))
        if layer is None:
            return
        self.iface.setActiveLayer(layer)
        add = find_action(self.win, "mActionAddFeature")
        if add is not None and not add.isChecked():
            add.trigger()

    def remove(self):
        self._timer.stop()
        project = QgsProject.instance()
        for signal in (project.layersAdded, project.layersRemoved):
            try:
                signal.disconnect(self.refresh)
            except (TypeError, RuntimeError):
                pass
        self.hide()
        if alive(self.win):
            self.win.removeDockWidget(self)
        self.setParent(None)
        self.deleteLater()


# ---------------------------------------------------------------- snapping


class SnappingToolBar(QToolBar):
    """ArcMap snapping toggles bound to the project snapping config."""

    TOGGLES = [
        ("vertex", "Vertex Snapping", "snap_vertex"),
        ("end", "End Snapping", "snap_end"),
        ("edge", "Edge Snapping", "snap_edge"),
        ("midpoint", "Midpoint Snapping", "snap_midpoint"),
        ("intersection", "Intersection Snapping", "snap_intersection"),
    ]

    def __init__(self, iface):
        super().__init__(tr("Snapping"), iface.mainWindow())
        self.iface = iface
        self.setObjectName("ArcMapSnappingToolBar")
        self.setIconSize(QSize(18, 18))
        self._syncing = False
        enable = find_action(iface.mainWindow(), "EnableSnappingAction")
        if enable is not None:
            self.addAction(enable)
            self.addSeparator()
        self.buttons = {}
        for key, tip, icon in self.TOGGLES:
            btn = tool_button(arcmap_icon(icon), tr(tip), checkable=True, size=18, parent=self)
            btn.setObjectName("ArcMapSnap_" + key)
            btn.toggled.connect(lambda on, k=key: self._set(k, on))
            self.addWidget(btn)
            self.buttons[key] = btn
        self.addSeparator()
        for name in ("TopologicalEditingAction", "EnableTracingAction", "SelfSnappingAction"):
            action = find_action(iface.mainWindow(), name)
            if action is not None:
                self.addAction(action)
        options = find_action(iface.mainWindow(), "mActionSnappingOptions")
        if options is not None:
            self.addSeparator()
            self.addAction(options)
        QgsProject.instance().snappingConfigChanged.connect(self.sync)
        self.sync()

    @staticmethod
    def _types():
        T = Qgis.SnappingType
        return {
            "vertex": T.Vertex,
            "end": getattr(T, "LineEndpoint", T.Vertex),
            "edge": T.Segment,
            "midpoint": getattr(T, "MiddleOfSegment", T.Segment),
        }

    def sync(self, *_):
        config = QgsProject.instance().snappingConfig()
        types = self._types()
        flags = config.typeFlag()
        self._syncing = True
        for key, btn in self.buttons.items():
            if key == "intersection":
                btn.setChecked(config.intersectionSnapping())
            else:
                btn.setChecked(bool(flags & types[key]))
        self._syncing = False

    def _set(self, key, on):
        if self._syncing:
            return
        project = QgsProject.instance()
        config = QgsSnappingConfig(project.snappingConfig())
        if key == "intersection":
            config.setIntersectionSnapping(on)
        else:
            types = self._types()
            flags = config.typeFlag()
            if on:
                flags |= types[key]
            else:
                flags &= ~types[key]
            config.setTypeFlag(flags)
            if on:
                config.setEnabled(True)
        project.setSnappingConfig(config)

    def remove(self):
        try:
            QgsProject.instance().snappingConfigChanged.disconnect(self.sync)
        except (TypeError, RuntimeError):
            pass
        self.hide()
        win = self.parent()
        if alive(win):
            win.removeToolBar(self)
        self.setParent(None)
        self.deleteLater()


def editor_actions(iface, changes, actions):
    """Start Editing / Stop Editing / Save Edits actions in ArcMap's words."""
    win = iface.mainWindow()

    def make(key, text, icon, callback):
        a = QAction(arcmap_icon(icon), text, win)
        a.setObjectName("ArcMapAction_" + key)
        a.triggered.connect(callback)
        actions[key] = a
        return a

    make("start_editing", tr("Start Editing"), "editor", lambda: start_editing(iface))
    make("stop_editing", tr("Stop Editing"), "stop_editing", lambda: stop_editing(iface))
    make("save_edits", tr("Save Edits"), "save_edits", lambda: stop_editing(iface, None, True))

    def undo(keys=("start_editing", "stop_editing", "save_edits")):
        for k in keys:
            a = actions.pop(k, None)
            if a is not None and alive(a):
                a.setParent(None)
                a.deleteLater()

    changes.add(undo)


def install_editing(iface, changes, actions):
    win = iface.mainWindow()
    dock = CreateFeaturesDock(iface)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    dock.hide()
    changes.add(dock.remove)
    actions["create_features_dock"] = dock.toggleViewAction()
    dock.toggleViewAction().setIcon(arcmap_icon("create_features"))
    toolbar = SnappingToolBar(iface)
    win.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
    toolbar.hide()
    changes.add(toolbar.remove)
    return dock, toolbar
