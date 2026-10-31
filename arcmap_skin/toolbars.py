# -*- coding: utf-8 -*-
"""ArcMap toolbars built from QGIS's own actions.

Two kinds of toolbars:

* **Built** toolbars (Standard, Tools, Editor, Layout, 3D Analyst, …) are new
  dockable ``QToolBar`` objects that hold QGIS's existing ``QAction`` objects,
  found by objectName. The QGIS toolbars they replace are hidden.
* **Renamed** toolbars are QGIS toolbars that keep their widgets (snapping,
  labelling, selection, raster, annotations …) and only get an ArcMap title.
  They are left visible or hidden according to the saved layout.

Spec grammar (``TOOLBARS`` items)::

    "mActionPan"                                   QGIS action
    ("alias", "mActionX", "Caption")               QGIS action, new caption
    ("custom", "go_to_xy")                         action from actions.py
    ("menubtn", key, "Tip", default_or_None, [items])   button with menu
    ("sub", "Title", [items])                      submenu inside a menubtn menu
    ("menu", "mMenuX", "Caption")                  existing QGIS menu as submenu
    ("dock", "Layers", "Table Of Contents", "toc") dock toggle
    ("toolbar", "ArcMapEditorToolBar", "Editor Toolbar", "editor")   toolbar toggle
    ("widget", "scale")                            widget factory
    SEP
"""

from qgis.gui import QgsScaleComboBox
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import QMenu, QToolBar, QToolButton

from .menus import ALIASES, SEP
from .util import (
    alive,
    arcmap_icon,
    find_action,
    find_dock,
    find_menu,
    find_toolbar,
    has_icon,
    set_restyle,
    top_toolbars,
    tr,
)

# QGIS toolbars replaced by built toolbars: hidden while the look is on.
HIDDEN_NATIVE = [
    "mFileToolBar",
    "mMapNavToolBar",
    "mAttributesToolBar",
    "mDigitizeToolBar",
    "mPluginToolBar",
    "mHelpToolBar",
    "mDataSourceManagerToolBar",
    "mLayerToolBar",
]

# QGIS toolbars kept (they hold widgets we cannot move): objectName → ArcMap title
RENAMED_NATIVE = {
    "mSnappingToolBar": "Snapping (QGIS)",
    "mLabelToolBar": "Labeling (QGIS)",
    "mSelectionToolBar": "Selection",
    "mRasterToolBar": "Image Analysis",
    "mAnnotationsToolBar": "Annotations (QGIS)",
    "mAdvancedDigitizeToolBar": "Advanced Editing",
    "mShapeDigitizeToolBar": "Shape Construction",
    "mMeshToolBar": "Mesh Editing",
    "mVectorToolBar": "Vector Tools",
    "mDatabaseToolBar": "Database",
    "mWebToolBar": "Web",
}

TOOLBARS = [
    ("ArcMapEditorToolBar", "Editor", [
        ("menubtn", "editor", "Editor", None, [
            ("custom", "start_editing"),
            ("custom", "stop_editing"),
            ("custom", "save_edits"),
            ("menu", "mActionAllEdits", "Current Edits"),
            SEP,
            "mActionMoveFeature", "mActionMoveFeatureCopy", "mActionSplitFeatures",
            "mActionMergeFeatures", "mActionMergeFeatureAttributes",
            ("custom", "buffer"),
            SEP,
            ("sub", "More Editing Tools", [
                "mActionAddRing", "mActionAddPart", "mActionFillRing", "mActionDeleteRing",
                "mActionDeletePart", "mActionOffsetCurve", "mActionReverseLine",
                "mActionTrimExtendFeature", "mActionSimplifyFeature", "mActionScaleFeature",
                "mActionRotatePointSymbols", "mActionOffsetPointSymbol",
            ]),
            SEP,
            "mActionSnappingOptions",
            "mActionOptions",
        ]),
        ("custom", "edit_tool"),
        "mActionModifyAnnotation",
        ("menubtn", "sketch", "Construction Tools", "mActionAddFeature", [
            "mActionAddFeature", SEP,
            "mActionDigitizeWithSegment", "mActionDigitizeWithCurve", "mActionStreamDigitize",
            "mActionDigitizeShape",
        ]),
        "EnableTracingAction",
        "mActionVertexTool",
        "mActionReshapeFeatures",
        "mActionSplitFeatures",
        "mActionSplitParts",
        "mActionRotateFeature",
        SEP,
        ("custom", "attributes_dock"),
        ("dock", "VertexEditor", "Sketch Properties", "sketch_properties"),
        ("custom", "create_features_dock"),
    ]),
    ("ArcMapLabelingToolBar", "Labeling", [
        ("custom", "label_manager"),
        ("custom", "pause_labeling"),
        "mActionShowUnplacedLabels",
        "mActionShowPinnedLabels",
        SEP,
        "mActionPinLabels",
        "mActionShowHideLabels",
        "mActionMoveLabel",
        "mActionRotateLabel",
        "mActionChangeLabelProperties",
        SEP,
        "mActionLabeling",
    ]),
    ("ArcMapDrawToolBar", "Draw", [
        "mActionModifyAnnotation",
        SEP,
        "mActionPolygonAnnotation", "mActionLineAnnotation", "mActionMarkerAnnotation",
        "mActionTextAnnotationatPoint", "mActionTextAnnotationalongLine", "mActionTextAnnotationinRectangle",
        "mActionPictureAnnotation",
        SEP,
        "mActionCreateAnnotationLayer",
    ]),
    ("ArcMapStandardToolBar", "Standard", [
        "mActionNewProject", "mActionOpenProject", "mActionSaveProject", "mActionNewPrintLayout",
        SEP,
        "mActionCutFeatures", "mActionCopyFeatures", "mActionPasteFeatures", "mActionDeleteSelected",
        SEP,
        "mActionUndo", "mActionRedo",
        SEP,
        ("menubtn", "add_data", "Add Data", "@add_data", [
            ("custom", "add_data"), ("basemaps",), "mActionDataSourceManager", SEP,
            "mActionAddOgrLayer", "mActionAddRasterLayer", "mActionAddDelimitedText",
            "mActionAddMeshLayer", "mActionAddPointCloudLayer", SEP,
            "mActionAddWmsLayer", "mActionAddXyzLayer", "mActionAddWfsLayer", "mActionAddWcsLayer",
            "mActionAddAfsLayer", "mActionAddVectorTileLayer", "mActionAddStacLayer", SEP,
            "mActionAddPgLayer", "mActionAddSpatiaLiteLayer", "mActionAddVirtualLayer", SEP,
            "mActionAddLayerDefinition", "mActionEmbedLayers",
        ]),
        ("widget", "scale"),
        SEP,
        ("toolbar", "ArcMapEditorToolBar", "Editor Toolbar", "editor"),
        ("dock", "Layers", "Table Of Contents", "toc"),
        ("dock", "Browser", "Catalog", "catalog"),
        ("dock", "ProcessingToolbox", "Search", "search"),
        ("custom", "arctoolbox_dock"),
        "mActionShowPythonDialog",
        "modelerAction",
        SEP,
        "mActionOpenTable",
    ]),
    ("ArcMapToolsToolBar", "Tools", [
        "mActionZoomIn", "mActionZoomOut", "mActionPan", "mActionZoomFullExtent",
        ("custom", "fixed_zoom_in"), ("custom", "fixed_zoom_out"),
        "mActionZoomLast", "mActionZoomNext",
        SEP,
        ("menubtn", "select_features", "Select Features", "mActionSelectFeatures", [
            "mActionSelectFeatures", "mActionSelectPolygon", "mActionSelectFreehand", "mActionSelectRadius",
            SEP, "mActionSelectByForm", "mActionSelectByExpression",
        ]),
        "mActionDeselectAll",
        "mActionModifyAnnotation",
        SEP,
        "mActionIdentify",
        "mActionFeatureAction",
        "mActionMapTips",
        ("menubtn", "measure", "Measure", "@measure_window", [
            ("custom", "measure_window"), SEP,
            "mActionMeasure", "mActionMeasureArea", "mActionMeasureAngle", "mActionMeasureBearing",
        ]),
        ("custom", "find"),
        ("custom", "go_to_xy"),
        SEP,
        "mActionTemporalController",
        "mActionNewMapCanvas",
    ]),
    ("ArcMapLayoutToolBar", "Layout", [
        "mActionNewPrintLayout", "mActionShowLayoutManager", "mActionNewReport",
        SEP,
        "mActionSaveMapAsImage", "mActionSaveMapAsPdf", "mActionDxfExport",
        SEP,
        "mActionDecorationTitle", "mActionDecorationNorthArrow", "mActionDecorationScaleBar",
        "mActionDecorationGrid",
    ]),
    ("ArcMapGeoreferencingToolBar", "Georeferencing", [
        "mActionShowGeoreferencer", "mActionShowRasterCalculator",
    ]),
    ("ArcMap3DAnalystToolBar", "3D Analyst", [
        "mActionNew3DMapCanvas", "mActionNew3DMapCanvasGlobe", "mActionManage3DMapViews",
        "mActionElevationProfile", "mActionElevationController",
    ]),
]

# ArcMap's standard scale list.
ARCMAP_SCALES = ["1:1000", "1:5000", "1:10000", "1:24000", "1:50000", "1:100000", "1:250000",
                 "1:500000", "1:1000000", "1:3000000", "1:10000000", "1:50000000"]

# Default ArcMap layout: (toolbar objectName, row) for the ones shown at first.
DEFAULT_VISIBLE = [
    ("ArcMapStandardToolBar", 0),
    ("ArcMapToolsToolBar", 0),
    ("ArcMapEditorToolBar", 1),
]


class ToolBarBuilder:
    def __init__(self, iface, changes, actions):
        self.iface = iface
        self.win = iface.mainWindow()
        self.changes = changes
        self.actions = actions
        self.built = []
        self._widgets = []

    # --------------------------------------------------------------- items

    def _alias(self, action, name):
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

    def resolve(self, item, parent):
        if isinstance(item, str):
            action = find_action(self.win, item)
            if action is not None:
                self._alias(action, item)
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
        if kind == "basemaps":
            from .basemaps import basemap_menu

            return basemap_menu(self.iface, parent).menuAction()
        if kind == "menu":
            menu = find_menu(self.win, item[1])
            if menu is None:
                action = find_action(self.win, item[1])
                menu = action.menu() if action is not None else None
            if menu is None:
                return None
            set_restyle(self.changes, menu.menuAction(), text=tr(item[2]))
            return menu.menuAction()
        if kind == "sub":
            sub = QMenu(tr(item[1]), parent)
            self.fill_menu(sub, item[2])
            return sub.menuAction() if sub.actions() else None
        if kind == "dock":
            dock = find_dock(self.win, item[1])
            if dock is None:
                return None
            action = dock.toggleViewAction()
            set_restyle(self.changes, action, text=tr(item[2]), icon=arcmap_icon(item[3]))
            return action
        if kind == "toolbar":
            tb = find_toolbar(self.win, item[1])
            if tb is None:
                return None
            action = tb.toggleViewAction()
            action.setText(tr(item[2]))
            action.setIcon(arcmap_icon(item[3]))
            return action
        if kind == "menubtn":
            return self.menu_button(item, parent)
        if kind == "widget":
            return self.widget(item[1], parent)
        return None

    def fill_menu(self, menu, items):
        pending = False
        for item in items:
            result = self.resolve(item, menu)
            if result is None:
                continue
            if result == "sep":
                pending = bool(menu.actions())
                continue
            if pending:
                menu.addSeparator()
                pending = False
            if isinstance(result, QAction):
                menu.addAction(result)

    def menu_button(self, item, parent):
        _, key, tip, default, items = item
        menu = QMenu(parent)
        menu.setObjectName("ArcMapMenu_" + key)
        self.fill_menu(menu, items)
        if not menu.actions():
            menu.deleteLater()
            return None
        button = QToolButton(parent)
        button.setObjectName("ArcMapButton_" + key)
        button.setMenu(menu)
        button.setToolTip(tr(tip))
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if default and default.startswith("@"):
            default_action = self.actions.get(default[1:])
        else:
            default_action = find_action(self.win, default) if default else None
        if default_action is not None:
            button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
            button.setDefaultAction(default_action)

            def remember(action, button=button, menu=menu):
                # ArcMap remembers the last tool picked from a split button.
                if action in menu.actions() and action.menu() is None and action.isCheckable():
                    button.setDefaultAction(action)

            menu.triggered.connect(remember)
        else:
            button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            button.setText(tr(tip) + " ")
            button.setIcon(arcmap_icon(key))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        return button

    def widget(self, key, parent):
        if key == "scale":
            canvas = self.iface.mapCanvas()
            box = QgsScaleComboBox(parent)
            box.setObjectName("ArcMapScaleBox")
            box.setToolTip(tr("Map Scale"))
            box.setMinimumWidth(110)
            box.setMaximumWidth(140)
            box.updateScales(ARCMAP_SCALES)
            box.setScale(canvas.scale())
            canvas.scaleChanged.connect(box.setScale)
            box.scaleChanged.connect(canvas.zoomScale)

            def undo(box=box, canvas=canvas):
                if alive(canvas):
                    try:
                        canvas.scaleChanged.disconnect(box.setScale)
                    except (TypeError, RuntimeError):
                        pass

            self.changes.add(undo)
            return box
        return None

    # ------------------------------------------------------------ toolbars

    def build_one(self, object_name, title, items):
        tb = QToolBar(tr(title), self.win)
        tb.setObjectName(object_name)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        tb.setAllowedAreas(Qt.ToolBarArea.AllToolBarAreas)
        tb.setFloatable(True)
        tb.setMovable(True)
        pending = False
        for item in items:
            result = self.resolve(item, tb)
            if result is None:
                continue
            if result == "sep":
                pending = bool(tb.actions())
                continue
            if pending:
                tb.addSeparator()
                pending = False
            if isinstance(result, QAction):
                tb.addAction(result)
            else:
                tb.addWidget(result)
        if not tb.actions():
            tb.deleteLater()
            return None
        self.win.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)
        self.built.append(tb)
        return tb

    def build(self):
        win = self.win
        for name in HIDDEN_NATIVE:
            tb = find_toolbar(win, name)
            if tb is not None:
                self.changes.set(tb, "visible", False)
        for name, title in RENAMED_NATIVE.items():
            tb = find_toolbar(win, name)
            if tb is not None:
                self.changes.set(tb, "windowTitle", tr(title))
        for object_name, title, items in TOOLBARS:
            self.build_one(object_name, title, items)
        built = list(self.built)

        def undo(win=win, built=built):
            for tb in built:
                if alive(tb):
                    tb.hide()
                    win.removeToolBar(tb)
                    tb.setParent(None)
                    tb.deleteLater()

        self.changes.add(undo)
        return built


def toolbars_menu(win, parent):
    """*Toolbars* menu: ArcMap toolbars, then QGIS toolbars, then add-ins."""
    menu = QMenu(tr("Toolbars"), parent)
    menu.setObjectName("ArcMapToolbarsMenu")

    def refill():
        menu.clear()
        ours, qgis, addins = [], [], []
        for tb in top_toolbars(win):
            name = tb.objectName()
            if name.startswith("ArcMap"):
                ours.append(tb)
            elif name in RENAMED_NATIVE or name in HIDDEN_NATIVE:
                qgis.append(tb)
            else:
                addins.append(tb)
        for group in (ours, qgis, addins):
            group.sort(key=lambda t: t.windowTitle().lower())
            for tb in group:
                action = tb.toggleViewAction()
                menu.addAction(action)
            if group and group is not addins:
                menu.addSeparator()

    menu.aboutToShow.connect(refill)
    refill()
    return menu


def reset_toolbars(win):
    """ArcMap default: Standard and Tools on row one, Editor on row two,
    add-in toolbars after them."""
    top = Qt.ToolBarArea.TopToolBarArea
    addins = []
    for tb in top_toolbars(win):
        name = tb.objectName()
        if name.startswith("ArcMap") or name in HIDDEN_NATIVE or name in RENAMED_NATIVE:
            tb.setVisible(False)
        elif tb.isVisible() and win.toolBarArea(tb) == top:
            addins.append(tb)
    # Re-adding a toolbar moves it to the end of the area, so the order of
    # the calls below is the order on screen.
    for tb in addins:
        win.removeToolBar(tb)
    previous_row = None
    for name, row in DEFAULT_VISIBLE:
        tb = find_toolbar(win, name)
        if tb is None:
            continue
        if previous_row is not None and row != previous_row:
            win.addToolBarBreak(top)
        win.addToolBar(top, tb)
        tb.setVisible(True)
        previous_row = row
    for tb in addins:
        win.addToolBar(top, tb)
        tb.setVisible(True)
    # QGIS toolbars that add-ins populate keep showing their content.
    for name in ("mWebToolBar", "mVectorToolBar", "mDatabaseToolBar"):
        tb = find_toolbar(win, name)
        if tb is not None and tb.actions() and tb not in addins:
            win.addToolBar(top, tb)
            tb.setVisible(True)


def hide_replaced_native(win):
    for name in HIDDEN_NATIVE:
        tb = find_toolbar(win, name)
        if tb is not None:
            tb.setVisible(False)


def build_toolbars(iface, changes, actions):
    return ToolBarBuilder(iface, changes, actions).build()
