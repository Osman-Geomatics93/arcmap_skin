# -*- coding: utf-8 -*-
"""ArcMap-style right-click menu for the Table Of Contents.

QGIS's own menu provider stays in place (replacing it would delete it); an
event filter on the layer tree viewport intercepts the context-menu event
and shows the ArcMap menu instead. The QGIS menu is still reachable from
the *QGIS* submenu at the bottom.
"""

from qgis.core import QgsLayerTree, QgsMapLayer, QgsProject, QgsVectorLayer
from qgis.PyQt.QtCore import QEvent, QObject
from qgis.PyQt.QtWidgets import QMenu

from .util import alive, arcmap_icon, find_action, tr


class TocMenu(QObject):
    def __init__(self, iface, actions):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.win = iface.mainWindow()
        self.view = iface.layerTreeView()
        self.custom = actions
        self._menu = None
        self._qgis_menu = None
        self.view.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802
        if event.type() == QEvent.Type.ContextMenu:
            self.show_menu(event.globalPos())
            return True
        return False

    # ------------------------------------------------------------ helpers

    def _qgis(self, name):
        return find_action(self.win, name)

    def _add(self, menu, name, text=None, icon=None):
        action = self._qgis(name)
        if action is None:
            return None
        if text is not None or icon is not None:
            # A proxy keeps the ArcMap caption without renaming the QGIS action.
            proxy = menu.addAction(arcmap_icon(icon) if icon else action.icon(), text or action.text())
            proxy.setEnabled(action.isEnabled())
            proxy.triggered.connect(action.trigger)
            return proxy
        menu.addAction(action)
        return action

    def show_menu(self, pos):
        node = self.view.currentNode()
        layer = self.view.currentLayer()
        menu = QMenu(self.view)
        menu.setObjectName("ArcMapTocContextMenu")
        self._menu = menu
        defaults = self.view.defaultActions()

        if node is not None and QgsLayerTree.isGroup(node):
            self._group_menu(menu, node, defaults)
        elif layer is not None:
            self._layer_menu(menu, layer, defaults)
        else:
            menu.addAction(defaults.actionAddGroup(menu))
            self._add(menu, "mActionDataSourceManager", tr("Add Data…"), "add_data")
            menu.addAction(arcmap_icon("full_extent"), tr("Full Extent"), lambda: self.iface.mapCanvas().zoomToFullExtent())

        # QGIS's own menu, for anything ArcMap never had.
        provider = self.view.menuProvider()
        if provider is not None:
            try:
                self._qgis_menu = provider.createContextMenu()
            except Exception:  # noqa: BLE001
                self._qgis_menu = None
            if self._qgis_menu is not None and self._qgis_menu.actions():
                menu.addSeparator()
                sub = menu.addMenu(tr("QGIS"))
                for a in self._qgis_menu.actions():
                    sub.addAction(a)
        menu.exec(pos)
        menu.deleteLater()
        self._menu = None

    def _group_menu(self, menu, node, defaults):
        menu.addAction(defaults.actionAddGroup(menu))
        menu.addAction(arcmap_icon("zoom_layer"), tr("Zoom To Layer"), lambda: self.iface.zoomToActiveLayer())
        menu.addSeparator()
        menu.addAction(defaults.actionCheckAndAllChildren(menu))
        menu.addAction(defaults.actionUncheckAndAllChildren(menu))
        menu.addAction(defaults.actionMutuallyExclusiveGroup(menu))
        menu.addSeparator()
        menu.addAction(defaults.actionRemoveGroupOrLayer(menu))
        menu.addAction(defaults.actionRenameGroupOrLayer(menu))
        menu.addSeparator()
        menu.addAction(defaults.actionGroupSetWmsData(menu)) if hasattr(defaults, "actionGroupSetWmsData") else None

    def _layer_menu(self, menu, layer, defaults):
        canvas = self.iface.mapCanvas()
        vector = isinstance(layer, QgsVectorLayer)
        self._add(menu, "mActionCopyLayer", tr("Copy"), "copy")
        menu.addAction(defaults.actionRemoveGroupOrLayer(menu))
        menu.addSeparator()
        if vector:
            self._add(menu, "mActionOpenTable", tr("Open Attribute Table"), "table")
            joins = menu.addMenu(arcmap_icon("spatial_join"), tr("Joins and Relates"))
            joins.addAction(tr("Join…"), lambda: self._run("native:joinattributestable"))
            joins.addAction(tr("Spatial Join…"), lambda: self._run("native:joinattributesbylocation"))
            joins.addAction(tr("Remove Join(s)"), lambda: self._remove_joins(layer))
            joins.addSeparator()
            joins.addAction(tr("Relate…"), lambda: self._properties_page(layer, "Relations"))
            menu.addSeparator()
        menu.addAction(arcmap_icon("zoom_layer"), tr("Zoom To Layer"), lambda: self.iface.zoomToActiveLayer())
        menu.addAction(tr("Zoom To Make Visible"), lambda: self._zoom_visible(layer))
        scale = menu.addMenu(tr("Visible Scale Range"))
        scale.addAction(tr("Set Minimum Scale"), lambda: self._set_scale(layer, "min"))
        scale.addAction(tr("Set Maximum Scale"), lambda: self._set_scale(layer, "max"))
        scale.addAction(tr("Clear Scale Range"), lambda: self._clear_scale(layer))
        self._add(scale, "mActionSetLayerScaleVisibility", tr("Set Scale Visibility…"))
        menu.addSeparator()
        if vector:
            sel = menu.addMenu(arcmap_icon("select_rect"), tr("Selection"))
            sel.addAction(arcmap_icon("zoom_selected"), tr("Zoom To Selected Features"), lambda: canvas.zoomToSelected(layer))
            sel.addAction(arcmap_icon("pan_selected"), tr("Pan To Selected Features"), lambda: canvas.panToSelected(layer))
            sel.addAction(arcmap_icon("clear_selected"), tr("Clear Selected Features"), layer.removeSelection)
            sel.addAction(arcmap_icon("switch_selection"), tr("Switch Selection"), layer.invertSelection)
            sel.addAction(arcmap_icon("select_all"), tr("Select All"), layer.selectAll)
            sel.addSeparator()
            sel.addAction(arcmap_icon("select_by_attributes"), tr("Select By Attributes…"),
                          lambda: self._select_by_attributes(layer))
            sel.addAction(tr("Make This The Only Selectable Layer"), lambda: self._only_selectable(layer))
            sel.addAction(tr("Create Layer From Selected Features"), lambda: self._run("native:saveselectedfeatures"))
            label = menu.addAction(arcmap_icon("labeling"), tr("Label Features"))
            label.setCheckable(True)
            label.setChecked(layer.labelsEnabled())
            label.toggled.connect(lambda on, lyr=layer: self._toggle_labels(lyr, on))
            self._add(menu, "mActionLabeling", tr("Labeling…"))
            edit = menu.addMenu(arcmap_icon("editor"), tr("Edit Features"))
            if layer.isEditable():
                edit.addAction(arcmap_icon("save_edits"), tr("Save Edits"), lambda: self._stop_editing(layer, True))
                edit.addAction(tr("Stop Editing"), lambda: self._stop_editing(layer))
            else:
                edit.addAction(arcmap_icon("editor"), tr("Start Editing"), lambda: self._start_editing(layer))
            menu.addSeparator()
            menu.addAction(arcmap_icon("select_by_attributes"), tr("Definition Query…"), lambda: self._definition_query(layer))
            menu.addSeparator()
        data = menu.addMenu(arcmap_icon("export_map"), tr("Data"))
        self._add(data, "mActionLayerSaveAs", tr("Export Data…"))
        self._add(data, "mActionLayerProperties", tr("Repair Data Source…"))
        data.addAction(tr("View Item Description…"), lambda: self._properties_page(layer, "Information"))
        self._add(menu, "mActionSaveLayerDefinition", tr("Save As Layer File…"))
        self._add(menu, "mActionCopyStyle", tr("Copy Symbology"))
        self._add(menu, "mActionPasteStyle", tr("Paste Symbology"))
        menu.addSeparator()
        menu.addAction(arcmap_icon("properties"), tr("Properties…"), lambda: self.iface.showLayerProperties(layer))

    # ------------------------------------------------------------ commands

    def _run(self, alg):
        from .actions import _run_algorithm

        _run_algorithm(alg)

    def _remove_joins(self, layer):
        for join in list(layer.vectorJoins()):
            layer.removeJoin(join.joinLayerId())
        layer.triggerRepaint()

    def _properties_page(self, layer, page):
        self.iface.showLayerProperties(layer, page)

    def _zoom_visible(self, layer):
        canvas = self.iface.mapCanvas()
        if not layer.hasScaleBasedVisibility():
            return
        scale = canvas.scale()
        if layer.minimumScale() and scale > layer.minimumScale():
            canvas.zoomScale(layer.minimumScale() * 0.99)
        elif layer.maximumScale() and scale < layer.maximumScale():
            canvas.zoomScale(layer.maximumScale() * 1.01)

    def _set_scale(self, layer, which):
        scale = self.iface.mapCanvas().scale()
        layer.setScaleBasedVisibility(True)
        if which == "min":
            layer.setMinimumScale(scale)
        else:
            layer.setMaximumScale(scale)
        layer.triggerRepaint()

    def _clear_scale(self, layer):
        layer.setScaleBasedVisibility(False)
        layer.triggerRepaint()

    def _toggle_labels(self, layer, on):
        if on and layer.labeling() is None:
            from qgis.core import QgsPalLayerSettings, QgsVectorLayerSimpleLabeling

            settings = QgsPalLayerSettings()
            fields = layer.fields()
            name = next((f.name() for f in fields if not f.isNumeric()), fields[0].name() if fields.count() else "")
            settings.fieldName = name
            layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(on)
        layer.triggerRepaint()

    def _only_selectable(self, layer):
        for other in QgsProject.instance().mapLayers().values():
            if not isinstance(other, QgsVectorLayer):
                continue
            flags = other.flags()
            if other is layer:
                flags |= QgsMapLayer.LayerFlag.Identifiable
            else:
                flags &= ~QgsMapLayer.LayerFlag.Identifiable
            other.setFlags(flags)

    def _select_by_attributes(self, layer):
        from .query_builder import open_select_by_attributes

        open_select_by_attributes(self.iface, layer)

    def _definition_query(self, layer):
        from .query_builder import open_definition_query

        open_definition_query(self.iface, layer)

    def _start_editing(self, layer):
        from .editing import start_editing

        start_editing(self.iface, layer)

    def _stop_editing(self, layer, save=None):
        from .editing import stop_editing

        stop_editing(self.iface, layer, save)

    def stop(self):
        if alive(self.view) and alive(self.view.viewport()):
            self.view.viewport().removeEventFilter(self)


def install_toc_menu(iface, changes, actions):
    menu = TocMenu(iface, actions)
    changes.add(menu.stop)
    return menu
