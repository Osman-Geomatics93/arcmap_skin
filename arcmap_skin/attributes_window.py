# -*- coding: utf-8 -*-
"""ArcMap's Attributes window (Editor toolbar ▸ Attributes): the selected
features of the layers being edited on the left, an editable attribute
form for the chosen feature on the right. Edits go into the layer's edit
session like any other QGIS form edit."""

from qgis.core import QgsExpression, QgsExpressionContext, QgsExpressionContextUtils, QgsProject, QgsVectorLayer
from qgis.gui import QgsAttributeEditorContext, QgsAttributeForm
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtWidgets import QDockWidget, QLabel, QScrollArea, QSplitter, QTreeWidget, QTreeWidgetItem

from .util import alive, arcmap_icon, tr

LAYER_ROLE = Qt.ItemDataRole.UserRole + 11
FID_ROLE = Qt.ItemDataRole.UserRole + 12


class AttributesDock(QDockWidget):
    def __init__(self, iface):
        super().__init__(tr("Attributes"), iface.mainWindow())
        self.iface = iface
        self.setObjectName("ArcMapAttributesDock")
        self.split = QSplitter(Qt.Orientation.Horizontal, self)
        self.tree = QTreeWidget(self.split)
        self.tree.setObjectName("ArcMapAttributesTree")
        self.tree.setHeaderHidden(True)
        self.tree.currentItemChanged.connect(self._current_changed)
        self.right = QScrollArea(self.split)
        self.right.setWidgetResizable(True)
        self.placeholder = QLabel(tr("Select features of a layer being edited to see their attributes."), self.right)
        self.placeholder.setWordWrap(True)
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.right.setWidget(self.placeholder)
        self.split.setStretchFactor(0, 1)
        self.split.setStretchFactor(1, 2)
        self.setWidget(self.split)
        self.form = None
        self._form_layer = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self.refresh)
        iface.mapCanvas().selectionChanged.connect(self.schedule)
        project = QgsProject.instance()
        project.layersAdded.connect(self.schedule)
        project.layersRemoved.connect(self.schedule)
        self.refresh()

    def schedule(self, *_):
        self._timer.start()

    def _layers(self):
        return [lyr for lyr in QgsProject.instance().mapLayers().values()
                if isinstance(lyr, QgsVectorLayer) and (lyr.isEditable() or lyr.selectedFeatureCount())]

    def refresh(self):
        if not self.isVisible():
            return
        current = self.tree.currentItem()
        keep = (current.data(0, LAYER_ROLE), current.data(0, FID_ROLE)) if current else (None, None)
        self.tree.blockSignals(True)
        self.tree.clear()
        first = None
        for layer in self._layers():
            top = QTreeWidgetItem(self.tree, [layer.name() + (tr(" (editing)") if layer.isEditable() else "")])
            top.setIcon(0, arcmap_icon("new_layer"))
            top.setData(0, LAYER_ROLE, layer.id())
            exp = QgsExpression(layer.displayExpression())
            ctx = QgsExpressionContext(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
            exp.prepare(ctx)
            for feat in layer.getSelectedFeatures():
                ctx.setFeature(feat)
                label = exp.evaluate(ctx)
                if label is None or str(label) == "":
                    label = str(feat.id())
                item = QTreeWidgetItem(top, [str(label)])
                item.setData(0, LAYER_ROLE, layer.id())
                item.setData(0, FID_ROLE, feat.id())
                if first is None:
                    first = item
                if keep == (layer.id(), feat.id()):
                    first = item
            top.setExpanded(True)
        self.tree.blockSignals(False)
        if first is not None:
            self.tree.setCurrentItem(first)
        else:
            self._show_form(None, None)

    def _current_changed(self, current, previous):
        if current is None:
            return
        fid = current.data(0, FID_ROLE)
        layer = QgsProject.instance().mapLayer(current.data(0, LAYER_ROLE))
        if fid is None or layer is None:
            return
        self._show_form(layer, fid)

    def _show_form(self, layer, fid):
        if self.form is not None and alive(self.form):
            if alive(self._form_layer) and self._form_layer.isEditable():
                self.form.save()
            self.form.deleteLater()
            self.form = None
        if layer is None:
            self.right.setWidget(self.placeholder if alive(self.placeholder) else QLabel(""))
            return
        feat = layer.getFeature(fid)
        ctx = QgsAttributeEditorContext()
        ctx.setVectorLayerTools(self.iface.vectorLayerTools())
        form = QgsAttributeForm(layer, feat, ctx, self.right)
        form.setMode(QgsAttributeEditorContext.Mode.SingleEditMode)
        self.form = form
        self._form_layer = layer
        self.right.setWidget(form)

    def remove(self):
        self._timer.stop()
        canvas = self.iface.mapCanvas()
        project = QgsProject.instance()
        for signal, slot in ((canvas.selectionChanged, self.schedule), (project.layersAdded, self.schedule),
                             (project.layersRemoved, self.schedule)):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        self.hide()
        win = self.parent()
        if alive(win):
            win.removeDockWidget(self)
        self.setParent(None)
        self.deleteLater()


def install_attributes_window(iface, changes, actions):
    win = iface.mainWindow()
    dock = AttributesDock(iface)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    dock.hide()
    toggle = dock.toggleViewAction()
    toggle.setIcon(arcmap_icon("attributes"))
    toggle.setText(tr("Attributes"))
    actions["attributes_dock"] = toggle
    dock.visibilityChanged.connect(lambda on: dock.refresh() if on else None)
    changes.add(dock.remove)
    return dock


def show_attributes(iface):
    from qgis.PyQt.QtWidgets import QDockWidget as _D

    dock = iface.mainWindow().findChild(_D, "ArcMapAttributesDock")
    if dock is not None:
        dock.show()
        dock.raise_()
        dock.refresh()
