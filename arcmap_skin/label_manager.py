# -*- coding: utf-8 -*-
"""ArcMap's Label Manager and Labeling toolbar.

* Label Manager pane: every vector layer with a check box that turns its
  labels on or off, a Properties button opening the layer's Labels tab.
* Pause Labeling: stops drawing labels on the map (map settings flag).
* View Unplaced Labels, Pin, Move, Rotate, Change Label: QGIS's own tools.
"""

from qgis.core import Qgis, QgsPalLayerSettings, QgsProject, QgsVectorLayer, QgsVectorLayerSimpleLabeling
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import QDockWidget, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from .util import alive, arcmap_icon, tr

LAYER_ROLE = Qt.ItemDataRole.UserRole + 21


class LabelManagerDock(QDockWidget):
    def __init__(self, iface):
        super().__init__(tr("Label Manager"), iface.mainWindow())
        self.iface = iface
        self.setObjectName("ArcMapLabelManagerDock")
        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(4, 4, 4, 4)
        self.tree = QTreeWidget(body)
        self.tree.setObjectName("ArcMapLabelTree")
        self.tree.setHeaderLabels([tr("Label Classes")])
        self.tree.itemChanged.connect(self._changed)
        self.tree.itemDoubleClicked.connect(lambda item, _c: QTimer.singleShot(0, lambda: self._properties(item)))
        layout.addWidget(self.tree, 1)
        row = QHBoxLayout()
        props = QPushButton(tr("Properties…"), body)
        props.clicked.connect(lambda: self._properties(self.tree.currentItem()))
        row.addWidget(props)
        row.addStretch(1)
        layout.addLayout(row)
        self.setWidget(body)
        self._syncing = False
        project = QgsProject.instance()
        project.layersAdded.connect(self.refresh)
        project.layersRemoved.connect(self.refresh)
        self._timer = QTimer(self)
        self._timer.setInterval(1500)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def refresh(self, *_):
        if not self.isVisible():
            return
        self._syncing = True
        self.tree.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if not isinstance(layer, QgsVectorLayer) or not layer.isSpatial():
                continue
            top = QTreeWidgetItem(self.tree, [layer.name()])
            top.setIcon(0, arcmap_icon("labeling"))
            top.setData(0, LAYER_ROLE, layer.id())
            top.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
            top.setCheckState(0, Qt.CheckState.Checked if layer.labelsEnabled() else Qt.CheckState.Unchecked)
            field = ""
            labeling = layer.labeling()
            if labeling is not None and hasattr(labeling, "settings"):
                try:
                    field = labeling.settings().fieldName
                except Exception:  # noqa: BLE001
                    field = ""
            child = QTreeWidgetItem(top, [tr("Default") + ((" – " + field) if field else "")])
            child.setData(0, LAYER_ROLE, layer.id())
            child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            top.setExpanded(True)
        self._syncing = False

    def _layer(self, item):
        return QgsProject.instance().mapLayer(item.data(0, LAYER_ROLE)) if item is not None else None

    def _changed(self, item, column):
        if self._syncing:
            return
        layer = self._layer(item)
        if layer is None:
            return
        on = item.checkState(0) == Qt.CheckState.Checked
        if on and layer.labeling() is None:
            settings = QgsPalLayerSettings()
            fields = layer.fields()
            name = next((f.name() for f in fields if not f.isNumeric()), fields[0].name() if fields.count() else "")
            settings.fieldName = name
            layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(on)
        layer.triggerRepaint()

    def _properties(self, item):
        layer = self._layer(item)
        if layer is not None:
            self.iface.showLayerProperties(layer, "Labels")

    def remove(self):
        self._timer.stop()
        project = QgsProject.instance()
        for signal in (project.layersAdded, project.layersRemoved):
            try:
                signal.disconnect(self.refresh)
            except (TypeError, RuntimeError):
                pass
        self.hide()
        win = self.parent()
        if alive(win):
            win.removeDockWidget(self)
        self.setParent(None)
        self.deleteLater()


def _labeling_flag():
    try:
        return Qgis.MapSettingsFlag.DrawLabeling
    except AttributeError:
        from qgis.core import QgsMapSettings

        return QgsMapSettings.Flag.DrawLabeling


def install_label_manager(iface, changes, actions):
    win = iface.mainWindow()
    canvas = iface.mapCanvas()
    dock = LabelManagerDock(iface)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    dock.hide()
    toggle = dock.toggleViewAction()
    toggle.setIcon(arcmap_icon("labeling"))
    toggle.setText(tr("Label Manager"))
    actions["label_manager"] = toggle
    dock.visibilityChanged.connect(lambda on: dock.refresh() if on else None)
    changes.add(dock.remove)

    pause = QAction(arcmap_icon("pause_drawing"), tr("Pause Labeling"), win)
    pause.setObjectName("ArcMapAction_pause_labeling")
    pause.setCheckable(True)
    flag = _labeling_flag()

    def toggle_labels(on):
        if not alive(canvas):
            return
        flags = canvas.mapSettings().flags()
        if on:
            flags &= ~flag
        else:
            flags |= flag
        canvas.setMapSettingsFlags(flags)
        canvas.refresh()

    pause.toggled.connect(toggle_labels)
    actions["pause_labeling"] = pause

    def undo():
        if pause.isChecked():
            toggle_labels(False)
        if alive(pause):
            pause.deleteLater()
        actions.pop("pause_labeling", None)
        actions.pop("label_manager", None)

    changes.add(undo)
    return dock
