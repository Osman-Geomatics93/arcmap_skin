# -*- coding: utf-8 -*-
"""The ArcMap menu bar: File, Edit, View, Bookmarks, Insert, Selection,
Geoprocessing, Customize, Windows, Help.

QGIS's own top-level menus are taken out of the menu bar (not hidden, so
their actions stay usable) and re-attached under *Customize ▸ QGIS Menus*.
The ArcMap menus are built from QGIS's own QActions, found by objectName,
plus the ArcMap-only commands from :mod:`actions`. Entries QGIS lacks are
simply skipped, so the same spec works across QGIS versions.

Spec grammar (``MENUS``)::

    "mActionPan"                        QGIS action as is
    ("alias", "mActionX", "Text…")      QGIS action with ArcMap caption/icon
    ("custom", "go_to_xy")              action from actions.custom_actions
    ("menu", "mMenuDecorations", "Decorations")  existing QGIS QMenu as submenu
    ("sub", "Zoom Data", [items])       new submenu
    ("dock", "Layers", "Table Of Contents", "toc")  dock toggle action
    ("toolbars",)                       placeholder: toolbars menu
    ("qgis_menus",)                     placeholder: QGIS menus submenu
    ("docks",)                          placeholder: all remaining docks
    SEP
"""

from qgis.PyQt.QtWidgets import QDockWidget, QMenu, QMenuBar

from .actions import custom_actions
from .util import alive, arcmap_icon, find_action, find_dock, find_menu, has_icon, set_restyle, tr

SEP = ("sep",)

# QGIS menus removed from the bar and re-attached under Customize ▸ QGIS Menus.
QGIS_MENUS = [
    "mProjectMenu",
    "mEditMenu",
    "mViewMenu",
    "mLayerMenu",
    "mSettingsMenu",
    "mPluginMenu",
    "mVectorMenu",
    "mRasterMenu",
    "mDatabaseMenu",
    "mMeshMenu",
    "mWebMenu",
    "mHelpMenu",
]

# QGIS action → (ArcMap caption, hand-drawn icon name)
ALIASES = {
    "mActionNewProject": ("New…", "new_map"),
    "mActionOpenProject": ("Open…", "open"),
    "mActionSaveProject": ("Save", "save"),
    "mActionSaveProjectAs": ("Save As…", "save_as"),
    "mActionDataSourceManager": ("Data Source Manager…", "add_data"),
    "mActionProjectProperties": ("Map Document Properties…", "map_properties"),
    "mActionShowLayoutManager": ("Page and Print Setup…", "page_setup"),
    "mActionNewPrintLayout": ("Print…", "print"),
    "mActionSaveMapAsImage": ("Export Map…", "export_map"),
    "mActionExit": ("Exit", "exit"),
    "mActionUndo": ("Undo", "undo"),
    "mActionRedo": ("Redo", "redo"),
    "mActionCutFeatures": ("Cut", "cut"),
    "mActionCopyFeatures": ("Copy", "copy"),
    "mActionPasteFeatures": ("Paste", "paste"),
    "mActionDeleteSelected": ("Delete", "delete"),
    "mActionSelectAll": ("Select All Elements", "select_all"),
    "mActionZoomFullExtent": ("Full Extent", "full_extent"),
    "mActionZoomToLayers": ("Zoom To Layer(s)", "zoom_layer"),
    "mActionZoomToSelected": ("Zoom To Selected Features", "zoom_selected"),
    "mActionPanToSelected": ("Pan To Selected Features", "pan_selected"),
    "mActionZoomLast": ("Go Back To Previous Extent", "prev_extent"),
    "mActionZoomNext": ("Go To Next Extent", "next_extent"),
    "mActionZoomIn": ("Zoom In", "zoom_in"),
    "mActionZoomOut": ("Zoom Out", "zoom_out"),
    "mActionPan": ("Pan", "pan"),
    "mActionIdentify": ("Identify", "identify"),
    "mActionMapTips": ("HTML Popup", "html_popup"),
    "mActionMeasure": ("Measure", "measure"),
    "mActionNewBookmark": ("Create Bookmark…", "bookmark_new"),
    "mActionShowBookmarkManager": ("Manage Bookmarks…", "bookmarks"),
    "mActionShowBookmarks": ("Bookmarks Panel", "bookmarks"),
    "mActionDraw": ("Refresh View", "refresh"),
    "mActionNewMapCanvas": ("Viewer Window", "viewer"),
    "mActionTemporalController": ("Time Slider", "time_slider"),
    "mActionSelectByExpression": ("Select By Attributes…", "select_by_attributes"),
    "mActionDeselectAll": ("Clear Selected Features", "clear_selected"),
    "mActionInvertSelection": ("Switch Selection", "switch_selection"),
    "mActionStatisticalSummary": ("Statistics…", "statistics"),
    "mActionManagePlugins": ("Add-In Manager…", "addins"),
    "mActionCustomization": ("Interface Customization…", "customize"),
    "mActionStyleManager": ("Style Manager…", "style_manager"),
    "mActionOptions": ("ArcMap Options…", "options"),
    "mActionShowPythonDialog": ("Python", "python"),
    "mActionToggleEditing": ("Start/Stop Editing", "editor"),
    "mActionSaveLayerEdits": ("Save Edits", "save_edits"),
    "mActionAddFeature": ("Straight Segment", "sketch"),
    "mActionVertexTool": ("Edit Vertices", "edit_vertices"),
    "mActionMoveFeature": ("Edit Tool", "edit_tool"),
    "mActionReshapeFeatures": ("Reshape Feature", "reshape"),
    "mActionSplitFeatures": ("Cut Polygons", "cut_polygons"),
    "mActionSplitParts": ("Split", "split"),
    "mActionRotateFeature": ("Rotate", "rotate"),
    "mActionMultiEditAttributes": ("Attributes", "attributes"),
    "mActionModifyAnnotation": ("Select Elements", "select_elements"),
    "mActionSelectFeatures": ("Select Features by Rectangle", "select_rect"),
    "mActionSelectPolygon": ("Select Features by Polygon", "select_polygon"),
    "mActionSelectFreehand": ("Select Features by Lasso", "select_lasso"),
    "mActionSelectRadius": ("Select Features by Circle", "select_circle"),
    "mActionOpenTable": ("Open Attribute Table", "table"),
    "mActionPolygonAnnotation": ("New Polygon", "draw_polygon"),
    "mActionLineAnnotation": ("New Line", "draw_line"),
    "mActionMarkerAnnotation": ("New Marker", "draw_marker"),
    "mActionTextAnnotationatPoint": ("New Text", "draw_text"),
    "mActionTextAnnotationalongLine": ("New Splined Text", "draw_text"),
    "mActionTextAnnotationinRectangle": ("New Rectangle Text", "draw_rect_text"),
    "mActionPictureAnnotation": ("New Picture", "picture"),
    "mActionLabeling": ("Label Manager…", "labeling"),
    "mActionHelpContents": ("ArcGIS Desktop Help", "help"),
    "mActionAbout": ("About QGIS", "about"),
    "mActionShowGeoreferencer": ("Georeferencing", "georeferencing"),
    "mActionFeatureAction": ("Hyperlink", "hyperlink"),
    "mActionShowRasterCalculator": ("Raster Calculator…", "raster_calculator"),
    "mActionOpenFieldCalc": ("Field Calculator…", "field_calculator"),
    "mActionNewMemoryLayer": ("New Scratch Layer…", "new_layer"),
    "toolboxAction": ("Processing Toolbox (QGIS)", "search"),
    "modelerAction": ("ModelBuilder", "model_builder"),
    "resultsViewer": ("Results", "results"),
    "optionsAction": ("Geoprocessing Options…", "environments"),
    "mActionDecorationTitle": ("Title", "title"),
    "mActionDecorationCopyright": ("Text", "text"),
    "mActionDecorationNorthArrow": ("North Arrow", "north_arrow"),
    "mActionDecorationScaleBar": ("Scale Bar", "scale_bar"),
    "mActionDecorationImage": ("Picture", "picture"),
    "mActionDecorationGrid": ("Grid", "grid"),
    "mActionNewReport": ("Report…", "report"),
    "mActionCreateAnnotationLayer": ("New Graphics Layer", "graphics_layer"),
}

MENUS = [
    ("ArcMapFileMenu", "&File", [
        "mActionNewProject",
        "mActionOpenProject",
        ("menu", "mRecentProjectsMenu", "Recent"),
        "mActionSaveProject",
        "mActionSaveProjectAs",
        "mActionRevertProject",
        SEP,
        ("custom", "add_data"),
        ("basemaps",),
        "mActionDataSourceManager",
        ("menu", "mAddLayerMenu", "Add Data From"),
        ("menu", "mNewLayerMenu", "New Layer"),
        SEP,
        "mActionProjectProperties",
        ("menu", "mProjectFromTemplateMenu", "New From Template"),
        SEP,
        "mActionShowLayoutManager",
        "mActionNewPrintLayout",
        ("menu", "menuImport_Export", "Export Map"),
        SEP,
        ("custom", "getting_started"),
        "mActionExit",
    ]),
    ("ArcMapEditMenu", "&Edit", [
        "mActionUndo",
        "mActionRedo",
        SEP,
        "mActionCutFeatures",
        "mActionCopyFeatures",
        "mActionPasteFeatures",
        ("menu", "mMenuPasteAs", "Paste Special"),
        "mActionDeleteSelected",
        SEP,
        "mActionSelectAll",
        ("menu", "mMenuSelect", "Select"),
        SEP,
        ("menu", "mMenuEditGeometry", "Edit Geometry"),
        ("menu", "mMenuEditAttributes", "Edit Attributes"),
        SEP,
        ("custom", "start_editing"),
        ("custom", "stop_editing"),
        ("custom", "save_edits"),
        ("menu", "mActionAllEdits", "Current Edits"),
    ]),
    ("ArcMapViewMenu", "&View", [
        ("custom", "data_view"),
        ("custom", "layout_view"),
        SEP,
        ("custom", "measure_window"),
        ("sub", "Zoom Data", "zoom_data", [
            "mActionZoomIn", "mActionZoomOut", "mActionPan", SEP,
            "mActionZoomFullExtent", "mActionZoomToLayers", "mActionZoomToSelected",
            "mActionPanToSelected", "mActionZoomActualSize", SEP,
            ("custom", "fixed_zoom_in"), ("custom", "fixed_zoom_out"), SEP,
            "mActionZoomLast", "mActionZoomNext",
        ]),
        ("menu", "mMenuLayerVisibility", "Layer Visibility"),
        ("menu", "mMenuDecorations", "Data Frame Decorations"),
        ("menu", "mMenuPreviewMode", "Preview Mode"),
        SEP,
        "mActionMapTips",
        "mActionNewMapCanvas",
        ("menu", "m3DMapViewsMenu", "3D Views"),
        SEP,
        ("toolbars",),
        ("custom", "status_bar"),
        "mActionToggleFullScreen",
        "mActionToggleMapOnly",
        SEP,
        "mActionDraw",
        ("custom", "pause_drawing"),
        SEP,
        "mActionProjectProperties",
    ]),
    ("ArcMapBookmarksMenu", "&Bookmarks", [
        "mActionNewBookmark",
        "mActionShowBookmarkManager",
        "mActionShowBookmarks",
        SEP,
        ("bookmarks",),
    ]),
    ("ArcMapInsertMenu", "&Insert", [
        "mActionNewPrintLayout",
        "mActionNewReport",
        SEP,
        "mActionDecorationTitle",
        "mActionDecorationCopyright",
        "mActionDecorationNorthArrow",
        "mActionDecorationScaleBar",
        "mActionDecorationImage",
        "mActionDecorationGrid",
        "mActionDecorationLayoutExtent",
        SEP,
        "mActionCreateAnnotationLayer",
        ("menu", "mMenuAnnotation", "Annotation"),
    ]),
    ("ArcMapSelectionMenu", "&Selection", [
        ("custom", "select_by_attributes"),
        ("custom", "select_by_location"),
        "mActionSelectByForm",
        SEP,
        "mActionZoomToSelected",
        "mActionPanToSelected",
        "mActionStatisticalSummary",
        SEP,
        "mActionDeselectAll",
        "mActionInvertSelection",
        "mActionSelectAll",
        "mActionReselect",
        "mActionDeselectActiveLayer",
        SEP,
        ("sub", "Interactive Selection Method", "select_method", [
            "mActionSelectFeatures", "mActionSelectPolygon", "mActionSelectFreehand", "mActionSelectRadius",
        ]),
        ("custom", "selectable_layers"),
    ]),
    ("ArcMapGeoprocessingMenu", "&Geoprocessing", [
        ("custom", "buffer"),
        ("custom", "clip"),
        ("custom", "intersect"),
        ("custom", "union"),
        ("custom", "merge"),
        ("custom", "dissolve"),
        SEP,
        ("custom", "arctoolbox_dock"),
        ("custom", "search_tools"),
        "toolboxAction",
        "optionsAction",
        "resultsViewer",
        "historyAction",
        "modelerAction",
        "mActionShowPythonDialog",
        SEP,
        "mActionShowRasterCalculator",
        "mActionOpenFieldCalc",
    ]),
    ("ArcMapCustomizeMenu", "&Customize", [
        ("toolbars",),
        "mActionManagePlugins",
        ("custom", "customize"),
        "mActionCustomization",
        SEP,
        "mActionStyleManager",
        "mActionConfigureShortcuts",
        "mActionCustomProjection",
        "mActionSnappingOptions",
        SEP,
        "mActionOptions",
        ("custom", "skin_options"),
        SEP,
        ("custom", "reset_layout"),
        ("qgis_menus",),
        ("custom", "arcmap_look"),
    ]),
    ("ArcMapWindowsMenu", "&Windows", [
        ("dock", "Overview", "Overview", "overview"),
        ("custom", "magnifier"),
        "mActionNewMapCanvas",
        SEP,
        ("dock", "Layers", "Table Of Contents", "toc"),
        ("dock", "Browser", "Catalog", "catalog"),
        ("dock", "ProcessingToolbox", "Search", "search"),
        ("custom", "arctoolbox_dock"),
        ("custom", "create_features_dock"),
        ("custom", "attributes_dock"),
        ("custom", "label_manager"),
        ("custom", "find"),
        ("dock", "LayerStyling", "Image Analysis / Symbology", "symbology"),
        ("dock", "Temporal Controller", "Time Slider", "time_slider"),
        SEP,
        ("custom", "reset_layout"),
        SEP,
        ("docks",),
    ]),
    ("ArcMapHelpMenu", "&Help", [
        "mActionHelpContents",
        "mActionHelpPyQgisAPI",
        ("menu", "mMenuPluginHelp", "Add-In Help"),
        SEP,
        "mActionReportaBug",
        "mActionQgisHomePage",
        "mActionCheckQgisVersion",
        SEP,
        "mActionAbout",
        ("custom", "about"),
    ]),
]

# dock objectNames that already have an ArcMap entry in Windows
_NAMED_DOCKS = {"Overview", "Layers", "Browser", "ProcessingToolbox", "LayerStyling"}


class MenuBuilder:
    def __init__(self, iface, changes, actions, toolbars_menu_factory=None):
        self.iface = iface
        self.win = iface.mainWindow()
        self.changes = changes
        self.actions = actions
        self.toolbars_menu_factory = toolbars_menu_factory
        self._borrowed = []  # (submenu, qgis_menu) re-attached QGIS menus

    # ---------------------------------------------------------------- items

    def resolve(self, item, parent):
        """Return a QAction (or None) for a spec item, creating submenus."""
        if isinstance(item, str):
            action = find_action(self.win, item)
            if action is None:
                return None
            self.alias(action, item)
            return action
        kind = item[0]
        if kind == "sep":
            return "sep"
        if kind == "alias":
            action = find_action(self.win, item[1])
            if action is None:
                return None
            set_restyle(self.changes, action, text=tr(item[2]))
            return action
        if kind == "custom":
            return self.actions.get(item[1])
        if kind == "menu":
            menu = find_menu(self.win, item[1])
            if menu is None:
                action = find_action(self.win, item[1])
                menu = action.menu() if action is not None else None
            if menu is None:
                return None
            # The menu keeps living where it is; its menuAction gets our caption.
            action = menu.menuAction()
            set_restyle(self.changes, action, text=tr(item[2]))
            return action
        if kind == "sub":
            sub = QMenu(tr(item[1]), parent)
            sub.setObjectName("ArcMapSub_" + item[2])
            self.fill(sub, item[3])
            return sub.menuAction() if sub.actions() else None
        if kind == "dock":
            dock = find_dock(self.win, item[1])
            if dock is None:
                return None
            action = dock.toggleViewAction()
            set_restyle(self.changes, action, text=tr(item[2]), icon=arcmap_icon(item[3]))
            return action
        if kind == "toolbars":
            if self.toolbars_menu_factory is None:
                return None
            menu = self.toolbars_menu_factory(parent)
            return menu.menuAction() if menu is not None else None
        if kind == "qgis_menus":
            return self.qgis_menus(parent).menuAction()
        if kind == "docks":
            return self.other_docks(parent)
        if kind == "bookmarks":
            return None
        if kind == "basemaps":
            from .basemaps import basemap_menu

            return basemap_menu(self.iface, parent).menuAction()
        return None

    def alias(self, action, name):
        alias = ALIASES.get(name)
        if alias is None:
            return
        text, icon = alias
        set_restyle(
            self.changes,
            action,
            text=tr(text),
            icon=arcmap_icon(icon) if icon and has_icon(icon) else None,
        )

    def fill(self, menu, items):
        pending_sep = False
        for item in items:
            result = self.resolve(item, menu)
            if result is None:
                continue
            if result == "sep":
                pending_sep = bool(menu.actions())
                continue
            if isinstance(result, list):
                for a in result:
                    menu.addAction(a)
                continue
            if pending_sep:
                menu.addSeparator()
                pending_sep = False
            menu.addAction(result)

    def other_docks(self, parent):
        acts = []
        for dock in self.win.findChildren(QDockWidget):
            if dock.parent() is not self.win or dock.objectName() in _NAMED_DOCKS:
                continue
            if not dock.objectName():
                continue
            acts.append(dock.toggleViewAction())
        acts.sort(key=lambda a: a.text().lower())
        return acts

    def qgis_menus(self, parent):
        sub = QMenu(tr("QGIS Menus"), parent)
        sub.setObjectName("ArcMapQgisMenus")
        for name in QGIS_MENUS:
            menu = find_menu(self.win, name)
            if menu is not None:
                sub.addMenu(menu)
                self._borrowed.append((sub, menu))
        processing = find_menu(self.win, "processing")
        if processing is not None:
            sub.addMenu(processing)
            self._borrowed.append((sub, processing))
        return sub

    # ------------------------------------------------------------------ bar

    def build(self):
        bar = self.win.menuBar()
        if not isinstance(bar, QMenuBar):
            return []
        # Take the QGIS menus off the bar, remembering where they were.
        original = list(bar.actions())
        removed = []
        for name in QGIS_MENUS + ["processing"]:
            menu = find_menu(self.win, name)
            if menu is None:
                continue
            act = menu.menuAction()
            if act in original:
                removed.append((act, original.index(act)))
        for act, _ in removed:
            bar.removeAction(act)

        first_left = bar.actions()[0] if bar.actions() else None
        built = []
        for object_name, title, items in MENUS:
            menu = QMenu(tr(title), bar)
            menu.setObjectName(object_name)
            self.fill(menu, items)
            if not menu.actions():
                menu.deleteLater()
                continue
            if first_left is not None:
                bar.insertMenu(first_left, menu)
            else:
                bar.addMenu(menu)
            built.append(menu)

        def undo(bar=bar, built=built, removed=removed, borrowed=self._borrowed, original=original):
            if not alive(bar):
                return
            for sub, menu in borrowed:
                if alive(sub) and alive(menu):
                    sub.removeAction(menu.menuAction())
            for menu in built:
                if alive(menu):
                    bar.removeAction(menu.menuAction())
                    menu.setParent(None)
                    menu.deleteLater()
            # Put the QGIS menus back in their original order.
            current = bar.actions()
            for act, index in removed:
                if not alive(act):
                    continue
                before = None
                for later in original[index + 1:]:
                    if later in current:
                        before = later
                        break
                if before is not None:
                    bar.insertAction(before, act)
                else:
                    bar.addAction(act)
                current = bar.actions()

        self.changes.add(undo)
        return built


def build_menus(iface, changes, actions=None, toolbars_menu_factory=None):
    """Build the ArcMap menu bar; returns (menus, actions)."""
    if actions is None:
        actions = custom_actions(iface, changes)
    builder = MenuBuilder(iface, changes, actions, toolbars_menu_factory)
    return builder.build(), actions
