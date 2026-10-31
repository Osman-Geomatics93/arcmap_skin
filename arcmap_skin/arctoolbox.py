# -*- coding: utf-8 -*-
"""ArcToolbox: QGIS, GDAL and GRASS algorithms arranged in ArcMap's toolbox
hierarchy (Analysis Tools ▸ Overlay ▸ Intersect …).

Only algorithms present in the running QGIS are shown. Double-click (or
Open) runs the normal Processing dialog; Batch opens the batch dialog.
The *Search For Tools* box filters the tree. The QGIS Processing Toolbox
keeps working as ArcMap's *Search* window.
"""

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QSize, Qt, QTimer
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QLineEdit,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .util import alive, arcmap_icon, tr

ALG_ROLE = Qt.ItemDataRole.UserRole + 3

# toolbox → toolset → [(ArcMap tool name, [candidate QGIS algorithm ids])]
TOOLBOXES = [
    ("Analysis Tools", [
        ("Extract", [
            ("Clip", ["native:clip"]),
            ("Select", ["native:extractbyexpression"]),
            ("Select by Attribute", ["native:extractbyattribute"]),
            ("Select by Location", ["native:extractbylocation"]),
            ("Split", ["native:splitvectorlayer"]),
            ("Table Select", ["native:extractbyexpression"]),
        ]),
        ("Overlay", [
            ("Erase", ["native:difference"]),
            ("Intersect", ["native:intersection"]),
            ("Spatial Join", ["native:joinattributesbylocation"]),
            ("Symmetrical Difference", ["native:symmetricaldifference"]),
            ("Union", ["native:union"]),
            ("Count Points in Polygon", ["native:countpointsinpolygon"]),
            ("Line Intersections", ["native:lineintersections"]),
            ("Split With Lines", ["native:splitwithlines"]),
        ]),
        ("Proximity", [
            ("Buffer", ["native:buffer"]),
            ("Multiple Ring Buffer", ["native:multiringconstantbuffer"]),
            ("Near", ["native:joinbynearest"]),
            ("Point Distance", ["qgis:distancematrix"]),
            ("Create Thiessen Polygons", ["native:voronoipolygons"]),
            ("Generate Near Table", ["native:joinbynearest"]),
        ]),
        ("Statistics", [
            ("Summary Statistics", ["qgis:statisticsbycategories"]),
            ("Frequency", ["qgis:statisticsbycategories"]),
            ("Field Statistics", ["qgis:basicstatisticsforfields"]),
            ("Mean Center", ["native:meancoordinates"]),
            ("Average Nearest Neighbor", ["native:nearestneighbouranalysis"]),
        ]),
    ]),
    ("Cartography Tools", [
        ("Generalization", [
            ("Simplify Line", ["native:simplifygeometries"]),
            ("Smooth Line", ["native:smoothgeometry"]),
            ("Aggregate Polygons", ["native:aggregate"]),
            ("Dissolve", ["native:dissolve"]),
        ]),
    ]),
    ("Conversion Tools", [
        ("To Raster", [
            ("Polygon to Raster", ["gdal:rasterize"]),
            ("Feature to Raster", ["gdal:rasterize"]),
            ("Raster to Other Format", ["gdal:translate"]),
        ]),
        ("From Raster", [
            ("Raster to Polygon", ["gdal:polygonize"]),
            ("Raster to Point", ["native:pixelstopoints"]),
            ("Raster to Polyline", ["gdal:contour"]),
            ("Raster to ASCII", ["gdal:gdal2xyz"]),
        ]),
        ("To Geodatabase", [
            ("Feature Class to Geodatabase", ["native:package"]),
            ("Feature Class to Feature Class", ["native:savefeatures"]),
        ]),
        ("To Shapefile", [
            ("Feature Class to Shapefile", ["native:savefeatures"]),
        ]),
        ("Excel / Table", [
            ("Table to Table", ["native:savefeatures"]),
        ]),
    ]),
    ("Data Management Tools", [
        ("Fields", [
            ("Add Field", ["native:addfieldtoattributestable"]),
            ("Delete Field", ["native:deletecolumn"]),
            ("Calculate Field", ["native:fieldcalculator"]),
            ("Alter Field", ["native:renametablefield"]),
            ("Refactor Fields", ["native:refactorfields"]),
        ]),
        ("Features", [
            ("Add XY Coordinates", ["native:addxyfields"]),
            ("Feature To Point", ["native:centroids"]),
            ("Feature To Line", ["native:polygonstolines"]),
            ("Feature Vertices To Points", ["native:extractvertices"]),
            ("Multipart To Singlepart", ["native:multiparttosingleparts"]),
            ("Polygon To Line", ["native:polygonstolines"]),
            ("Points To Line", ["native:pointstopath"]),
            ("Copy Features", ["native:savefeatures"]),
            ("Minimum Bounding Geometry", ["qgis:minimumboundinggeometry", "native:minimumboundinggeometry"]),
            ("Bearing Distance To Line", ["native:projectpointcartesian"]),
        ]),
        ("General", [
            ("Merge", ["native:mergevectorlayers"]),
            ("Append", ["native:mergevectorlayers"]),
            ("Delete Identical", ["native:deleteduplicategeometries"]),
            ("Sort", ["native:orderbyexpression"]),
        ]),
        ("Generalization", [
            ("Dissolve", ["native:dissolve"]),
            ("Eliminate Polygon Part", ["native:deleteholes"]),
        ]),
        ("Geometry", [
            ("Add Geometry Attributes", ["qgis:exportaddgeometrycolumns"]),
            ("Convex Hull", ["native:convexhull"]),
            ("Check Geometry", ["native:checkvalidity"]),
            ("Repair Geometry", ["native:fixgeometries"]),
        ]),
        ("Joins", [
            ("Add Join", ["native:joinattributestable"]),
            ("Spatial Join", ["native:joinattributesbylocation"]),
        ]),
        ("Projections and Transformations", [
            ("Project", ["native:reprojectlayer"]),
            ("Define Projection", ["native:assignprojection"]),
            ("Project Raster", ["gdal:warpreproject"]),
        ]),
        ("Raster", [
            ("Clip (Raster)", ["gdal:cliprasterbyextent"]),
            ("Extract by Mask", ["gdal:cliprasterbymasklayer"]),
            ("Mosaic To New Raster", ["gdal:merge"]),
            ("Build Virtual Raster", ["gdal:buildvirtualraster"]),
            ("Resample", ["gdal:warpreproject"]),
            ("Build Pyramids", ["gdal:overviews"]),
            ("Copy Raster", ["gdal:translate"]),
            ("Create Constant Raster", ["native:createconstantrasterlayer"]),
            ("Create Random Raster", ["native:createrandomnormalrasterlayer"]),
        ]),
        ("Sampling", [
            ("Create Fishnet", ["native:creategrid"]),
            ("Create Random Points", ["native:randompointsinextent"]),
            ("Create Random Points in Polygons", ["native:randompointsinpolygons"]),
            ("Generate Points Along Lines", ["native:pointsalonglines"]),
        ]),
        ("Table", [
            ("Delete Identical", ["native:deleteduplicategeometries"]),
            ("Truncate Table", ["native:truncatetable"]),
        ]),
        ("Indexes", [
            ("Add Spatial Index", ["native:createspatialindex"]),
            ("Add Attribute Index", ["native:createattributeindex"]),
        ]),
    ]),
    ("Editing Tools", [
        ("Editing", [
            ("Snap", ["native:snapgeometries"]),
            ("Densify", ["native:densifygeometries"]),
            ("Generalize", ["native:simplifygeometries"]),
            ("Erase Point", ["native:difference"]),
            ("Transform Features", ["native:affinetransform"]),
        ]),
    ]),
    ("Spatial Analyst Tools", [
        ("Surface", [
            ("Slope", ["native:slope", "gdal:slope"]),
            ("Aspect", ["native:aspect", "gdal:aspect"]),
            ("Hillshade", ["native:hillshade", "gdal:hillshade"]),
            ("Contour", ["gdal:contour"]),
            ("Curvature", ["gdal:roughness"]),
            ("Viewshed", ["grass:r.viewshed"]),
        ]),
        ("Distance", [
            ("Euclidean Distance", ["gdal:proximity"]),
            ("Cost Distance", ["grass:r.cost"]),
        ]),
        ("Map Algebra", [
            ("Raster Calculator", ["native:rastercalc", "qgis:rastercalculator"]),
            ("Raster Calculator (GDAL)", ["gdal:rastercalculator"]),
            ("Cell Statistics", ["native:cellstatistics"]),
        ]),
        ("Reclass", [
            ("Reclassify", ["native:reclassifybytable"]),
            ("Reclassify (GRASS)", ["grass:r.reclass"]),
        ]),
        ("Zonal", [
            ("Zonal Statistics", ["native:zonalstatisticsfb"]),
            ("Zonal Histogram", ["native:zonalhistogram"]),
        ]),
        ("Interpolation", [
            ("IDW", ["qgis:idwinterpolation"]),
            ("Natural Neighbor / TIN", ["qgis:tininterpolation"]),
            ("Spline", ["grass:v.surf.rst"]),
        ]),
        ("Extraction", [
            ("Extract by Mask", ["gdal:cliprasterbymasklayer"]),
            ("Extract by Rectangle", ["gdal:cliprasterbyextent"]),
            ("Extract Values to Points", ["native:rastersampling"]),
            ("Sample", ["native:rastersampling"]),
        ]),
        ("Hydrology", [
            ("Fill", ["grass:r.fill.dir"]),
            ("Flow Direction / Accumulation", ["grass:r.watershed"]),
            ("Stream to Feature", ["grass:r.stream.extract"]),
            ("Flow Length", ["grass:r.flow"]),
        ]),
        ("Neighborhood", [
            ("Focal Statistics", ["grass:r.neighbors"]),
            ("Sieve", ["gdal:sieve"]),
        ]),
        ("Density", [
            ("Kernel Density", ["qgis:heatmapkerneldensityestimation"]),
        ]),
        ("Generalization", [
            ("Resample", ["grass:r.resample", "gdal:warpreproject"]),
            ("Fill NoData", ["native:fillnodata", "gdal:fillnodata"]),
        ]),
        ("Raster Analysis", [
            ("Raster Layer Statistics", ["native:rasterlayerstatistics"]),
            ("Unique Values Report", ["native:rasterlayeruniquevaluesreport"]),
            ("Surface Volume", ["native:rastersurfacevolume"]),
            ("Fuzzy Membership", ["native:fuzzifyrasterlinearmembership"]),
        ]),
    ]),
    ("3D Analyst Tools", [
        ("Raster Surface", [
            ("Slope", ["native:slope", "gdal:slope"]),
            ("Aspect", ["native:aspect", "gdal:aspect"]),
            ("Hillshade", ["native:hillshade", "gdal:hillshade"]),
            ("Contour", ["gdal:contour"]),
            ("Terrain Ruggedness Index", ["gdal:triterrainruggednessindex"]),
            ("Topographic Position Index", ["gdal:tpitopographicpositionindex"]),
        ]),
        ("TIN", [
            ("Create TIN", ["native:delaunaytriangulation"]),
            ("TIN to Raster", ["qgis:tininterpolation"]),
        ]),
        ("3D Features", [
            ("Add Z Information", ["native:extractzvalues"]),
            ("Feature To 3D By Attribute", ["native:setzvalue"]),
            ("Drop Z / M", ["native:dropmzvalues"]),
        ]),
    ]),
    ("Network Analyst Tools", [
        ("Analysis", [
            ("Shortest Path", ["native:shortestpathpointtopoint"]),
            ("Service Area", ["native:serviceareafrompoint"]),
        ]),
    ]),
    ("Spatial Statistics Tools", [
        ("Measuring Geographic Distributions", [
            ("Mean Center", ["native:meancoordinates"]),
            ("Average Nearest Neighbor", ["native:nearestneighbouranalysis"]),
        ]),
        ("Mapping Clusters", [
            ("Density-based Clustering", ["native:dbscanclustering"]),
            ("K-Means Clustering", ["native:kmeansclustering"]),
        ]),
    ]),
]


# Order of ArcMap's toolboxes in the tree; anything else follows alphabetically.
TOOLBOX_ORDER = [
    "3D Analyst Tools", "Analysis Tools", "Cartography Tools", "Conversion Tools",
    "Data Management Tools", "Editing Tools", "Geostatistical Analyst Tools",
    "Linear Referencing Tools", "Multidimension Tools", "Network Analyst Tools",
    "Spatial Analyst Tools", "Spatial Statistics Tools", "My Toolboxes",
]

# Every other Processing algorithm is filed by (provider, group) into an
# ArcMap toolbox / toolset. Group keys are matched case-insensitively as
# prefixes of the QGIS group name.
GROUP_RULES = {
    "native": {
        "vector analysis": ("Analysis Tools", "Vector Analysis"),
        "vector overlay": ("Analysis Tools", "Overlay"),
        "vector selection": ("Analysis Tools", "Extract"),
        "vector geometry": ("Data Management Tools", "Features"),
        "vector general": ("Data Management Tools", "General"),
        "vector table": ("Data Management Tools", "Fields"),
        "vector creation": ("Data Management Tools", "Sampling"),
        "vector coverage": ("Data Management Tools", "Topology"),
        "vector tiles": ("Conversion Tools", "To Vector Tiles"),
        "check geometry": ("Data Management Tools", "Topology"),
        "fix geometry": ("Data Management Tools", "Topology"),
        "raster analysis": ("Spatial Analyst Tools", "Raster Analysis"),
        "raster terrain analysis": ("Spatial Analyst Tools", "Surface"),
        "raster creation": ("Data Management Tools", "Raster"),
        "raster tools": ("Data Management Tools", "Raster"),
        "interpolation": ("Spatial Analyst Tools", "Interpolation"),
        "network analysis": ("Network Analyst Tools", "Analysis"),
        "database": ("Data Management Tools", "Database"),
        "file tools": ("Data Management Tools", "File"),
        "layer tools": ("Data Management Tools", "Layers and Table Views"),
        "cartography": ("Cartography Tools", "Cartography"),
        "plots": ("Cartography Tools", "Graphs"),
        "mesh": ("3D Analyst Tools", "Mesh"),
        "3d tiles": ("3D Analyst Tools", "3D Tiles"),
        "metadata tools": ("Data Management Tools", "Metadata"),
        "modeler tools": ("Data Management Tools", "Modeler"),
        "gps": ("Data Management Tools", "GPS"),
        "graphics": ("Cartography Tools", "Graphics"),
    },
    "gdal": {
        "raster analysis": ("Spatial Analyst Tools", "Raster Analysis (GDAL)"),
        "raster conversion": ("Conversion Tools", "Raster (GDAL)"),
        "raster extraction": ("Spatial Analyst Tools", "Extraction"),
        "raster miscellaneous": ("Data Management Tools", "Raster (GDAL)"),
        "raster projections": ("Data Management Tools", "Projections and Transformations"),
        "vector conversion": ("Conversion Tools", "Vector (GDAL)"),
        "vector geoprocessing": ("Analysis Tools", "Overlay (GDAL)"),
        "vector miscellaneous": ("Data Management Tools", "General (GDAL)"),
    },
    "pdal": {
        "point cloud conversion": ("3D Analyst Tools", "Point Cloud Conversion"),
        "point cloud data management": ("3D Analyst Tools", "Point Cloud Data Management"),
        "point cloud extraction": ("3D Analyst Tools", "Point Cloud Extraction"),
    },
    "3d": {"": ("3D Analyst Tools", "3D Features")},
    "grass": {
        "raster": ("Spatial Analyst Tools", "GRASS Raster"),
        "vector": ("Analysis Tools", "GRASS Vector"),
        "imagery": ("Spatial Analyst Tools", "Image Analysis (GRASS)"),
        "": ("Spatial Analyst Tools", "GRASS"),
    },
    "model": {"": ("My Toolboxes", "Models")},
    "project": {"": ("My Toolboxes", "Project Models")},
    "script": {"": ("My Toolboxes", "Scripts")},
}
GROUP_RULES["qgis"] = GROUP_RULES["native"]


def _registry():
    return QgsApplication.processingRegistry()


def _resolve(candidates):
    reg = _registry()
    for alg_id in candidates:
        alg = reg.algorithmById(alg_id)
        if alg is not None:
            return alg
    return None


def _auto_place(alg):
    """(toolbox, toolset) for an algorithm not in the curated tables."""
    provider = alg.provider()
    pid = provider.id() if provider else ""
    group = (alg.group() or "").lower()
    rules = GROUP_RULES.get(pid)
    if rules:
        for key, target in rules.items():
            if key and group.startswith(key):
                return target
        if "" in rules:
            return rules[""]
    name = provider.name() if provider else pid
    return ("%s Tools" % name, alg.group() or tr("Tools"))


def _hidden(alg):
    try:
        from qgis.core import QgsProcessingAlgorithm

        flags = alg.flags()
        return bool(flags & QgsProcessingAlgorithm.Flag.FlagHideFromToolbox) or bool(
            flags & QgsProcessingAlgorithm.Flag.FlagNotAvailableInStandaloneTool) and False
    except Exception:  # noqa: BLE001
        return False


class ArcToolboxDock(QDockWidget):
    def __init__(self, iface):
        super().__init__(tr("ArcToolbox"), iface.mainWindow())
        self.iface = iface
        self.setObjectName("ArcMapToolboxDock")
        body = QWidget(self)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self.search = QLineEdit(body)
        self.search.setObjectName("ArcMapToolboxSearch")
        self.search.setPlaceholderText(tr("Search For Tools"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter)
        layout.addWidget(self.search)
        self.tree = QTreeWidget(body)
        self.tree.setObjectName("ArcMapToolboxTree")
        self.tree.setHeaderHidden(True)
        self.tree.setIconSize(QSize(16, 16))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.tree.itemDoubleClicked.connect(self._open_item)
        layout.addWidget(self.tree, 1)
        self.setWidget(body)
        self.fill()

    def fill(self):
        """Curated ArcMap tools first, then every other algorithm by rules."""
        self.tree.clear()
        toolbox_icon = arcmap_icon("arctoolbox")
        toolset_icon = arcmap_icon("toolset")
        tool_icon = arcmap_icon("tool")
        toolboxes = {}  # name → (item, {toolset: item})
        placed = set()
        total = 0

        def toolbox_item(name):
            if name not in toolboxes:
                item = QTreeWidgetItem([tr(name)])
                item.setIcon(0, toolbox_icon)
                toolboxes[name] = (item, {})
            return toolboxes[name]

        def toolset_item(toolbox, toolset):
            tb_item, sets = toolbox_item(toolbox)
            if toolset not in sets:
                item = QTreeWidgetItem(tb_item, [tr(toolset)])
                item.setIcon(0, toolset_icon)
                sets[toolset] = item
            return sets[toolset]

        def add_tool(parent, caption, alg):
            item = QTreeWidgetItem(parent, [caption])
            item.setIcon(0, tool_icon)
            item.setData(0, ALG_ROLE, alg.id())
            tip = alg.shortDescription() or alg.displayName()
            item.setToolTip(0, "%s  (%s)" % (tip, alg.id()))
            return item

        for toolbox, toolsets in TOOLBOXES:
            for toolset, tools in toolsets:
                for name, candidates in tools:
                    alg = _resolve(candidates)
                    if alg is None:
                        continue
                    add_tool(toolset_item(toolbox, toolset), tr(name), alg)
                    placed.add(alg.id())
                    total += 1
        for alg in _registry().algorithms():
            if alg.id() in placed or _hidden(alg):
                continue
            toolbox, toolset = _auto_place(alg)
            add_tool(toolset_item(toolbox, toolset), alg.displayName(), alg)
            placed.add(alg.id())
            total += 1

        def order(name):
            return (TOOLBOX_ORDER.index(name) if name in TOOLBOX_ORDER else len(TOOLBOX_ORDER) - 1, name)

        for name in sorted(toolboxes, key=order):
            tb_item, sets = toolboxes[name]
            tb_item.sortChildren(0, Qt.SortOrder.AscendingOrder)
            for ts_item in sets.values():
                ts_item.sortChildren(0, Qt.SortOrder.AscendingOrder)
            self.tree.addTopLevelItem(tb_item)
        self.tree.collapseAll()
        self.total = total
        self.setToolTip(tr("%d tools") % total)

    def filter(self, text):
        text = text.strip().lower()

        def visit(item):
            if item.childCount() == 0:
                hit = not text or text in item.text(0).lower() or text in (item.toolTip(0) or "").lower()
                item.setHidden(not hit)
                return hit
            any_hit = False
            for i in range(item.childCount()):
                any_hit = visit(item.child(i)) or any_hit
            item.setHidden(not any_hit)
            item.setExpanded(bool(text) and any_hit)
            return any_hit

        for i in range(self.tree.topLevelItemCount()):
            visit(self.tree.topLevelItem(i))

    def _alg_id(self, item):
        return item.data(0, ALG_ROLE) if item is not None else None

    def _open_item(self, item, column=0):
        alg_id = self._alg_id(item)
        if alg_id:
            from .actions import _run_algorithm

            QTimer.singleShot(0, lambda: _run_algorithm(alg_id))

    def _batch(self, alg_id):
        try:
            from processing.gui.BatchAlgorithmDialog import BatchAlgorithmDialog

            alg = _registry().createAlgorithmById(alg_id)
            dlg = BatchAlgorithmDialog(alg, self.iface.mainWindow())
            dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dlg.show()
        except Exception:  # noqa: BLE001
            self._open_item(self.tree.currentItem())

    def _help(self, alg_id):
        from qgis.PyQt.QtCore import QUrl
        from qgis.PyQt.QtGui import QDesktopServices

        alg = _registry().algorithmById(alg_id)
        url = alg.helpUrl() if alg is not None else ""
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _context_menu(self, pos):
        item = self.tree.itemAt(pos)
        alg_id = self._alg_id(item)
        if not alg_id:
            return
        menu = QMenu(self.tree)
        menu.addAction(arcmap_icon("tool"), tr("Open"), lambda: self._open_item(item))
        menu.addAction(tr("Batch…"), lambda: self._batch(alg_id))
        menu.addSeparator()
        menu.addAction(arcmap_icon("help"), tr("Tool Help"), lambda: self._help(alg_id))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def focus_search(self):
        self.show()
        self.raise_()
        self.search.setFocus(Qt.FocusReason.OtherFocusReason)
        self.search.selectAll()

    def remove(self):
        self.hide()
        win = self.parent()
        if alive(win):
            win.removeDockWidget(self)
        self.setParent(None)
        self.deleteLater()


def install_arctoolbox(iface, changes, actions):
    win = iface.mainWindow()
    dock = ArcToolboxDock(iface)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    changes.add(dock.remove)
    toggle = dock.toggleViewAction()
    toggle.setIcon(arcmap_icon("arctoolbox"))
    toggle.setText(tr("ArcToolbox"))
    actions["arctoolbox_dock"] = toggle
    return dock
