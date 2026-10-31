# -*- coding: utf-8 -*-
"""ArcMap's Edit Tool: one black arrow that selects features by click or
drag-rectangle, moves selected features by dragging them, opens vertex
editing on double-click, and has ArcMap's right-click menu (Move…, Rotate,
Edit Vertices, Attributes…, Copy, Delete, Unselect All).

Works on the active layer when it is being edited, otherwise on the first
layer in an edit session (the Create Features window sets the active one).
"""

from qgis.core import (
    Qgis,
    QgsFeatureRequest,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsTolerance,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QAction, QColor
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QMenu

from .util import alive, arcmap_icon, find_action, tr


class MoveDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle(tr("Move"))
        form = QFormLayout(self)
        self.dx = QDoubleSpinBox(self)
        self.dy = QDoubleSpinBox(self)
        for box in (self.dx, self.dy):
            box.setRange(-1e9, 1e9)
            box.setDecimals(6)
        form.addRow(tr("Delta X:"), self.dx)
        form.addRow(tr("Delta Y:"), self.dy)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)


class ArcMapEditTool(QgsMapTool):
    def __init__(self, iface):
        super().__init__(iface.mapCanvas())
        self.iface = iface
        self.win = iface.mainWindow()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._press = None
        self._mode = None  # "move" | "rect"
        self.was_used = False
        self._bands = []
        self._rect_band = QgsRubberBand(self.canvas(), Qgis.GeometryType.Polygon)
        self._rect_band.setColor(QColor(0, 120, 215, 60))
        self._rect_band.setStrokeColor(QColor(0, 120, 215))
        self._rect_band.setWidth(1)
        self._rect_band.hide()

    # ----------------------------------------------------------- helpers

    def layer(self):
        active = self.iface.activeLayer()
        if isinstance(active, QgsVectorLayer) and active.isEditable():
            return active
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer) and lyr.isEditable():
                return lyr
        return active if isinstance(active, QgsVectorLayer) else None

    def _search_rect(self, layer, point):
        tol = QgsTolerance.toleranceInMapUnits(8, layer, self.canvas().mapSettings(), QgsTolerance.UnitType.Pixels)
        p = self.toLayerCoordinates(layer, point)
        return QgsRectangle(p.x() - tol, p.y() - tol, p.x() + tol, p.y() + tol)

    def _feature_at(self, layer, point):
        rect = self._search_rect(layer, point)
        request = QgsFeatureRequest().setFilterRect(rect).setFlags(QgsFeatureRequest.Flag.ExactIntersect)
        for feat in layer.getFeatures(request):
            return feat
        return None

    def _clear_bands(self):
        for band in self._bands:
            self.canvas().scene().removeItem(band)
        self._bands = []

    def _make_bands(self, layer):
        self._clear_bands()
        for feat in layer.getSelectedFeatures():
            geom = feat.geometry()
            if geom.isEmpty():
                continue
            band = QgsRubberBand(self.canvas(), QgsWkbTypes.geometryType(geom.wkbType()))
            band.setColor(QColor(255, 0, 0, 120))
            band.setWidth(2)
            band.setToGeometry(geom, layer)
            self._bands.append(band)

    # ------------------------------------------------------------ events

    def canvasPressEvent(self, e):  # noqa: N802
        if e.button() != Qt.MouseButton.LeftButton:
            return
        layer = self.layer()
        self._press = e.mapPoint()
        if layer is None:
            self._mode = "rect"
            return
        feat = self._feature_at(layer, self._press)
        if feat is None:
            self._mode = "rect"
            return
        shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if feat.id() not in layer.selectedFeatureIds():
            layer.selectByIds([feat.id()], Qgis.SelectBehavior.AddToSelection if shift else Qgis.SelectBehavior.SetSelection)
        elif shift:
            layer.deselect(feat.id())
            self._mode = None
            return
        self.iface.setActiveLayer(layer)
        self._mode = "move" if layer.isEditable() else None
        if self._mode == "move":
            self._make_bands(layer)

    def canvasMoveEvent(self, e):  # noqa: N802
        if self._press is None:
            return
        if self._mode == "move":
            dx = e.mapPoint().x() - self._press.x()
            dy = e.mapPoint().y() - self._press.y()
            layer = self.layer()
            for band, feat in zip(self._bands, layer.getSelectedFeatures() if layer else []):
                geom = QgsGeometry(feat.geometry())
                p = self.toLayerCoordinates(layer, QgsPointXY(self._press.x() + dx, self._press.y() + dy))
                p0 = self.toLayerCoordinates(layer, self._press)
                geom.translate(p.x() - p0.x(), p.y() - p0.y())
                band.setToGeometry(geom, layer)
        elif self._mode == "rect":
            rect = QgsRectangle(self._press, e.mapPoint())
            self._rect_band.setToGeometry(QgsGeometry.fromRect(rect), None)
            self._rect_band.show()

    def canvasReleaseEvent(self, e):  # noqa: N802
        if e.button() == Qt.MouseButton.RightButton:
            self.context_menu(e)
            return
        if self._press is None:
            return
        layer = self.layer()
        if self._mode == "move" and layer is not None:
            p1 = self.toLayerCoordinates(layer, self._press)
            p2 = self.toLayerCoordinates(layer, e.mapPoint())
            dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
            pixels = (e.pixelPoint() - self.toCanvasCoordinates(self._press)).manhattanLength()
            if pixels > 3:
                layer.beginEditCommand(tr("Move features"))
                for fid in layer.selectedFeatureIds():
                    layer.translateFeature(fid, dx, dy)
                layer.endEditCommand()
                layer.triggerRepaint()
        elif self._mode == "rect":
            self._rect_band.hide()
            rect = QgsRectangle(self._press, e.mapPoint())
            target = layer or self.iface.activeLayer()
            if isinstance(target, QgsVectorLayer):
                shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                if rect.width() < 1e-9 and rect.height() < 1e-9:
                    if not shift:
                        target.removeSelection()
                else:
                    lrect = self.toLayerCoordinates(target, rect)
                    target.selectByRect(lrect, Qgis.SelectBehavior.AddToSelection if shift else Qgis.SelectBehavior.SetSelection)
        self._clear_bands()
        self._press = None
        self._mode = None

    def canvasDoubleClickEvent(self, e):  # noqa: N802
        layer = self.layer()
        if layer is None:
            return
        feat = self._feature_at(layer, e.mapPoint())
        if feat is not None:
            layer.selectByIds([feat.id()])
            action = find_action(self.win, "mActionVertexToolActiveLayer") or find_action(self.win, "mActionVertexTool")
            if action is not None:
                action.trigger()

    def activate(self):
        self.was_used = True
        super().activate()

    def deactivate(self):
        self._clear_bands()
        self._rect_band.hide()
        self._press = None
        self._mode = None
        super().deactivate()

    # ------------------------------------------------------- context menu

    def context_menu(self, e):
        layer = self.layer()
        menu = QMenu(self.canvas())
        has_sel = isinstance(layer, QgsVectorLayer) and layer.selectedFeatureCount() > 0
        editing = has_sel and layer.isEditable()

        def qgis(name, text=None, icon=None):
            a = find_action(self.win, name)
            if a is None:
                return None
            if text is None:
                menu.addAction(a)
                return a
            proxy = menu.addAction(arcmap_icon(icon) if icon else a.icon(), text)
            proxy.triggered.connect(a.trigger)
            proxy.setEnabled(a.isEnabled())
            return proxy

        move = menu.addAction(arcmap_icon("edit_tool"), tr("Move…"))
        move.setEnabled(editing)
        move.triggered.connect(lambda: self.move_by_dialog(layer))
        qgis("mActionRotateFeature", tr("Rotate"), "rotate")
        if qgis("mActionVertexToolActiveLayer", tr("Edit Vertices"), "edit_vertices") is None:
            qgis("mActionVertexTool", tr("Edit Vertices"), "edit_vertices")
        menu.addSeparator()
        attrs = menu.addAction(arcmap_icon("attributes"), tr("Attributes…"))
        attrs.setEnabled(has_sel)
        attrs.triggered.connect(lambda: self.open_attributes(layer))
        menu.addSeparator()
        qgis("mActionCopyFeatures", tr("Copy"), "copy")
        qgis("mActionPasteFeatures", tr("Paste"), "paste")
        qgis("mActionDeleteSelected", tr("Delete"), "delete")
        menu.addSeparator()
        unsel = menu.addAction(arcmap_icon("clear_selected"), tr("Unselect All"))
        unsel.triggered.connect(lambda: layer.removeSelection() if layer else None)
        menu.exec(e.globalPos() if hasattr(e, "globalPos") else self.canvas().mapToGlobal(e.pos()))

    def move_by_dialog(self, layer):
        dlg = MoveDialog(self.win)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        layer.beginEditCommand(tr("Move features"))
        for fid in layer.selectedFeatureIds():
            layer.translateFeature(fid, dlg.dx.value(), dlg.dy.value())
        layer.endEditCommand()
        layer.triggerRepaint()

    def open_attributes(self, layer):
        from .attributes_window import show_attributes

        show_attributes(self.iface)


def install_edit_tool(iface, changes, actions):
    tool = ArcMapEditTool(iface)
    action = QAction(arcmap_icon("edit_tool"), tr("Edit Tool"), iface.mainWindow())
    action.setObjectName("ArcMapAction_edit_tool")
    action.setCheckable(True)
    action.setToolTip(tr("Edit Tool: click to select, drag to move, double-click to edit vertices"))
    tool.setAction(action)
    action.triggered.connect(lambda: iface.mapCanvas().setMapTool(tool))
    actions["edit_tool"] = action
    canvas = iface.mapCanvas()

    def undo():
        # The canvas remembers the last non-zoom tool and re-activates it
        # after a zoom; make sure that is never our (about to vanish) tool.
        if alive(canvas):
            if canvas.mapTool() is tool:
                canvas.unsetMapTool(tool)
            if tool.was_used:
                pan = iface.actionPan()
                if pan is not None:
                    pan.trigger()
        tool.setAction(None)
        if alive(action):
            action.deleteLater()
        actions.pop("edit_tool", None)

    changes.add(undo)
    return tool
