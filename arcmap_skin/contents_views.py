# -*- coding: utf-8 -*-
"""Table Of Contents "List By" views: Drawing Order, Source, Visibility, Selection.

Drawing Order is QGIS's own layer tree. The other three are a plain
``QTreeWidget`` filled from the project and swapped in place of the native
tree, the way ArcMap switches TOC views. Nothing in the project is changed
by showing a view; check boxes write back through the layer tree.
"""

import os

from qgis.core import QgsMapLayer, QgsProject, QgsProviderRegistry, QgsVectorLayer
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .util import alive, arcmap_icon, tool_button, tr

LAYER_ROLE = Qt.ItemDataRole.UserRole + 1

VIEWS = [
    ("order", "List By Drawing Order", "list_by_drawing_order"),
    ("source", "List By Source", "list_by_source"),
    ("visibility", "List By Visibility", "list_by_visibility"),
    ("selection", "List By Selection", "list_by_selection"),
]


def _source_group(layer):
    """Folder / database / service a layer comes from, as ArcMap shows it."""
    provider = layer.providerType()
    source = layer.source()
    try:
        parts = QgsProviderRegistry.instance().decodeUri(provider, source)
    except Exception:  # noqa: BLE001
        parts = {}
    path = parts.get("path") if isinstance(parts, dict) else None
    if path:
        return os.path.dirname(os.path.normpath(path)) or path
    url = parts.get("url") if isinstance(parts, dict) else None
    if url:
        return url
    if provider in ("postgres", "mssql", "oracle", "hana"):
        host = parts.get("host") or parts.get("service") or provider
        db = parts.get("dbname") or ""
        return "%s/%s" % (host, db) if db else host
    if provider in ("wms", "wfs", "arcgisfeatureserver", "arcgismapserver", "vectortile", "wcs"):
        return source.split("url=")[-1].split("&")[0] if "url=" in source else provider
    return provider


def _layer_icon(layer):
    from qgis.core import QgsIconUtils

    try:
        return QgsIconUtils.iconForLayer(layer)
    except Exception:  # noqa: BLE001
        return QIcon()


class ContentsViews(QWidget):
    """Header with List By buttons plus the custom list for the three views."""

    def __init__(self, iface, dock, tree_view, actions):
        super().__init__(dock)
        self.iface = iface
        self.dock = dock
        self.tree_view = tree_view
        self.view = "order"
        self.setObjectName("ArcMapTocHeader")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(2)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = {}
        for key, tip, icon in VIEWS:
            btn = tool_button(arcmap_icon(icon), tr(tip), checkable=True, size=16, parent=self)
            btn.setObjectName("ArcMapListBy_" + key)
            btn.clicked.connect(lambda _=False, k=key: self.show_view(k))
            self.group.addButton(btn)
            layout.addWidget(btn)
            self.buttons[key] = btn
        self.buttons["order"].setChecked(True)
        layout.addStretch(1)
        self.title = QLabel("", self)
        self.title.setObjectName("ArcMapTocViewTitle")
        layout.addWidget(self.title)
        # The few QGIS layer-panel tools ArcMap users expect, on the right
        defaults = tree_view.defaultActions() if hasattr(tree_view, "defaultActions") else None
        if defaults is not None:
            add_group = defaults.actionAddGroup(self)
            add_group.setIcon(arcmap_icon("folder"))
            add_group.setToolTip(tr("New Group Layer"))
            b = tool_button(add_group.icon(), tr("New Group Layer"), size=16, parent=self)
            b.setDefaultAction(add_group)
            layout.addWidget(b)
        self.expand_button = tool_button(arcmap_icon("sort_desc"), tr("Expand All Layers"), size=16, parent=self)
        self.expand_button.clicked.connect(lambda: tree_view.expandAllNodes())
        layout.addWidget(self.expand_button)
        self.collapse_button = tool_button(arcmap_icon("sort_asc"), tr("Collapse All Layers"), size=16, parent=self)
        self.collapse_button.clicked.connect(lambda: tree_view.collapseAllNodes())
        layout.addWidget(self.collapse_button)

        self.list = QTreeWidget(dock)
        self.list.setObjectName("ArcMapTocList")
        self.list.setHeaderHidden(True)
        self.list.setRootIsDecorated(True)
        self.list.setUniformRowHeights(True)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        self.list.itemChanged.connect(self._toggled)
        self.list.itemClicked.connect(self._clicked)
        self.list.itemDoubleClicked.connect(self._double_clicked)
        self.list.hide()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self.refresh)

        project = QgsProject.instance()
        project.layersAdded.connect(self.schedule)
        project.layersRemoved.connect(self.schedule)
        project.layerTreeRoot().visibilityChanged.connect(self._visibility_changed)
        iface.mapCanvas().selectionChanged.connect(self._selection_changed)
        iface.mapCanvas().layersChanged.connect(self.schedule)

        selectable = actions.get("selectable_layers")
        if selectable is not None:
            selectable.triggered.connect(self._show_selection_view)

    # ----------------------------------------------------------- switching

    def _show_selection_view(self):
        self.dock.setVisible(True)
        self.dock.raise_()
        self.buttons["selection"].setChecked(True)
        self.show_view("selection")

    def show_view(self, key):
        self.view = key
        native = key == "order"
        self.tree_view.setVisible(native)
        self.list.setVisible(not native)
        self.title.setText("" if native else tr(dict((k, t) for k, t, _ in VIEWS)[key]).replace("List By ", ""))
        self.refresh()

    def schedule(self, *_):
        if self.view != "order":
            self._timer.start()

    def _visibility_changed(self, *_):
        if self.view in ("source", "visibility"):
            self._timer.start()

    def _selection_changed(self, *_):
        if self.view == "selection":
            self._timer.start()

    # -------------------------------------------------------------- filling

    def _layers(self):
        root = QgsProject.instance().layerTreeRoot()
        return [n for n in root.findLayers() if n.layer() is not None]

    def refresh(self):
        if self.view == "order" or not self.list.isVisible():
            return
        self.list.blockSignals(True)
        self.list.clear()
        try:
            if self.view == "source":
                groups = {}
                for node in self._layers():
                    key = _source_group(node.layer())
                    groups.setdefault(key, []).append(node)
                for key in sorted(groups, key=str.lower):
                    top = QTreeWidgetItem(self.list, [key])
                    top.setIcon(0, arcmap_icon("folder"))
                    top.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    for node in groups[key]:
                        self._layer_item(top, node, check="visible")
                self.list.expandAll()
            elif self.view == "visibility":
                for node in self._layers():
                    self._layer_item(self.list, node, check="visible")
            elif self.view == "selection":
                for node in self._layers():
                    layer = node.layer()
                    if not isinstance(layer, QgsVectorLayer):
                        continue
                    item = self._layer_item(self.list, node, check="identifiable")
                    count = layer.selectedFeatureCount()
                    if count:
                        item.setText(0, "%s  (%d)" % (layer.name(), count))
        finally:
            self.list.blockSignals(False)

    def _layer_item(self, parent, node, check):
        layer = node.layer()
        item = QTreeWidgetItem(parent, [layer.name()])
        item.setIcon(0, _layer_icon(layer))
        item.setData(0, LAYER_ROLE, layer.id())
        item.setData(0, LAYER_ROLE + 1, check)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable)
        if check == "visible":
            item.setCheckState(0, Qt.CheckState.Checked if node.isVisible() else Qt.CheckState.Unchecked)
        else:
            flags = layer.flags()
            on = bool(flags & QgsMapLayer.LayerFlag.Identifiable)
            item.setCheckState(0, Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
            item.setToolTip(0, tr("Checked layers can be identified and selected on the map"))
        return item

    # -------------------------------------------------------------- editing

    def _layer(self, item):
        if item is None:
            return None
        lid = item.data(0, LAYER_ROLE)
        return QgsProject.instance().mapLayer(lid) if lid else None

    def _node(self, item):
        layer = self._layer(item)
        return QgsProject.instance().layerTreeRoot().findLayer(layer.id()) if layer else None

    def _toggled(self, item, column):
        layer = self._layer(item)
        if layer is None:
            return
        on = item.checkState(0) == Qt.CheckState.Checked
        if item.data(0, LAYER_ROLE + 1) == "visible":
            node = self._node(item)
            if node is not None:
                node.setItemVisibilityChecked(on)
        else:
            flags = layer.flags()
            if on:
                flags |= QgsMapLayer.LayerFlag.Identifiable
            else:
                flags &= ~QgsMapLayer.LayerFlag.Identifiable
            layer.setFlags(flags)

    def _clicked(self, item, column):
        layer = self._layer(item)
        if layer is not None:
            self.iface.setActiveLayer(layer)

    def _double_clicked(self, item, column):
        layer = self._layer(item)
        if layer is not None:
            # After the event finishes: the properties dialog is modal.
            QTimer.singleShot(0, lambda: self.iface.showLayerProperties(layer) if alive(layer) else None)

    def _context_menu(self, pos):
        item = self.list.itemAt(pos)
        layer = self._layer(item)
        if layer is None:
            return
        self.iface.setActiveLayer(layer)
        menu = QMenu(self.list)
        canvas = self.iface.mapCanvas()
        if isinstance(layer, QgsVectorLayer):
            menu.addAction(arcmap_icon("table"), tr("Open Attribute Table"), lambda: self.iface.showAttributeTable(layer))
            menu.addAction(arcmap_icon("zoom_selected"), tr("Zoom To Selected Features"), lambda: canvas.zoomToSelected(layer))
            menu.addAction(arcmap_icon("clear_selected"), tr("Clear Selected Features"), layer.removeSelection)
            menu.addAction(arcmap_icon("select_all"), tr("Select All"), layer.selectAll)
            menu.addSeparator()
        menu.addAction(arcmap_icon("zoom_layer"), tr("Zoom To Layer"), lambda: self.iface.zoomToActiveLayer())
        menu.addAction(arcmap_icon("properties"), tr("Properties…"), lambda: self.iface.showLayerProperties(layer))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    # -------------------------------------------------------------- removal

    def remove(self):
        project = QgsProject.instance()
        for signal, slot in (
            (project.layersAdded, self.schedule),
            (project.layersRemoved, self.schedule),
            (project.layerTreeRoot().visibilityChanged, self._visibility_changed),
        ):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        canvas = self.iface.mapCanvas()
        if alive(canvas):
            for signal, slot in ((canvas.selectionChanged, self._selection_changed), (canvas.layersChanged, self.schedule)):
                try:
                    signal.disconnect(slot)
                except (TypeError, RuntimeError):
                    pass
        if alive(self.tree_view):
            self.tree_view.setVisible(True)
        if alive(self.list):
            self.list.hide()
            self.list.setParent(None)
            self.list.deleteLater()
        self.hide()
        self.setParent(None)
        self.deleteLater()


def dress_contents(iface, changes, dock, actions):
    """Add the List By header and views to the Layers dock."""
    tree_view = iface.layerTreeView()
    if tree_view is None:
        return None
    container = tree_view.parentWidget()
    layout = container.layout() if container is not None else None
    if not isinstance(layout, QVBoxLayout):
        return None
    views = ContentsViews(iface, dock, tree_view, actions)
    layout.insertWidget(0, views)
    # ArcMap's TOC has only the List By row: hide QGIS's layer-panel toolbar
    from qgis.PyQt.QtWidgets import QToolBar

    for tb in container.findChildren(QToolBar):
        if tb is not views and tb.parent() is container:
            changes.set(tb, "visible", False)
    index = layout.indexOf(tree_view)
    layout.insertWidget(index + 1 if index >= 0 else layout.count(), views.list)
    changes.add(views.remove)
    changes.set(tree_view, "alternatingRowColors", False)
    return views
