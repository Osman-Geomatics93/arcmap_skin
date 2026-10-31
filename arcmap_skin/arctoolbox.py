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


def _registry():
    return QgsApplication.processingRegistry()


def _resolve(candidates):
    reg = _registry()
    for alg_id in candidates:
        alg = reg.algorithmById(alg_id)
        if alg is not None:
            return alg
    return None


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
        self.tree.clear()
        toolbox_icon = arcmap_icon("arctoolbox")
        toolset_icon = arcmap_icon("toolset")
        tool_icon = arcmap_icon("tool")
        total = 0
        for toolbox, toolsets in TOOLBOXES:
            tb_item = QTreeWidgetItem(self.tree, [tr(toolbox)])
            tb_item.setIcon(0, toolbox_icon)
            for toolset, tools in toolsets:
                ts_item = QTreeWidgetItem(tb_item, [tr(toolset)])
                ts_item.setIcon(0, toolset_icon)
                for name, candidates in tools:
                    alg = _resolve(candidates)
                    if alg is None:
                        continue
                    item = QTreeWidgetItem(ts_item, [tr(name)])
                    item.setIcon(0, tool_icon)
                    item.setData(0, ALG_ROLE, alg.id())
                    item.setToolTip(0, "%s  (%s)" % (alg.displayName(), alg.id()))
                    total += 1
                if ts_item.childCount() == 0:
                    tb_item.removeChild(ts_item)
            if tb_item.childCount() == 0:
                self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(tb_item))
        self.tree.collapseAll()
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
