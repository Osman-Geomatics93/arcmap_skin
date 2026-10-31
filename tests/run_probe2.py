"""Probe QGIS internals needed for the ArcMap features; writes probe2_result.txt."""

import os
import traceback

from qgis.PyQt.QtCore import QEventLoop, QTimer

HERE = "D:/QGIS_Plugins/Arcmap_Skin/tests"
OUT = os.path.join(HERE, "probe2_result.txt")
lines = []

ALGS = """native:clip native:extractbyexpression native:splitvectorlayer native:difference native:intersection
native:joinattributesbylocation native:symmetricaldifference native:union native:buffer native:multiringconstantbuffer
native:joinbynearest qgis:distancematrix qgis:statisticsbycategories qgis:basicstatisticsforfields native:simplifygeometries
native:smoothgeometry native:aggregate gdal:rasterize gdal:polygonize native:pixelstopoints native:package native:savefeatures
native:addfieldtoattributestable native:deletecolumn native:fieldcalculator native:addxyfields native:centroids
native:polygonstolines native:extractvertices native:multiparttosingleparts native:pointstopath native:minimumboundinggeometry
native:dissolve native:mergevectorlayers native:reprojectlayer native:assignprojection gdal:warpreproject native:joinattributestable
gdal:cliprasterbyextent gdal:cliprasterbymasklayer gdal:merge gdal:overviews native:rastercalc qgis:rastercalculator native:creategrid
native:randompointsinextent native:deleteduplicategeometries native:checkvalidity native:fixgeometries qgis:exportaddgeometrycolumns
native:slope native:aspect native:hillshade gdal:contour gdal:proximity native:reclassifybytable native:zonalstatisticsfb
native:zonalhistogram qgis:idwinterpolation qgis:tininterpolation native:rastersampling qgis:heatmapkerneldensityestimation
native:shortestpathpointtopoint native:serviceareafrompoint native:snapgeometries native:densifygeometries native:extractbylocation
native:selectbylocation native:selectbyexpression native:intersection native:countpointsinpolygon native:convexhull native:voronoipolygons
native:delaunaytriangulation native:lineintersections native:splitwithlines native:mergelines native:explodelines native:boundary
native:collect native:promotetomulti native:refactorfields native:deleteholes native:orientedminimumboundingbox native:extractbyattribute
native:extractbyextent native:randompointsinpolygons native:randompointsonlines native:pointsalonglines native:translategeometry
native:rotatefeatures native:fillnodata gdal:fillnodata gdal:translate gdal:aspect gdal:slope gdal:hillshade gdal:roughness gdal:tri gdal:tpi
native:rasterlayerstatistics native:rasterlayeruniquevaluesreport native:rasterlayerzonalstats native:cellstatistics native:rasterbooleanand
native:rastersurfacevolume native:rasterize native:createconstantrasterlayer native:createrandomnormalrasterlayer gdal:sieve
gdal:nearblack gdal:rastercalculator gdal:gdal2xyz grass:r.fill.dir grass:r.watershed grass:r.neighbors grass:r.cost grass:r.viewshed
grass:r.flow grass:r.stream.extract grass:v.kernel grass:r.surf.idw grass:v.surf.rst grass:r.resample grass:r.reclass grass:r.mapcalc.simple
qgis:kernelsurface native:dbscanclustering native:kmeansclustering native:sumlinelengths native:meancoordinates native:nearestneighbouranalysis
qgis:linestopolygons native:polygonize native:setzvalue native:dropmzvalues native:exportlayersto... native:spatialindex native:createspatialindex
gdal:gdalinfo native:raiseexception native:tilesxyzdirectory gdal:buildvirtualraster gdal:translate native:exportmeshvertices
native:filterverticesbyz native:geometrybyexpression native:bufferbym qgis:regularpoints native:randompointsinlayerbounds
native:convertgeometrytype native:pointonsurface native:poleofinaccessibility native:offsetline native:singlesidedbuffer native:wedgebuffers
native:taperedbuffer native:truncatetable native:dropgeometries native:createattributeindex native:fieldcalculator native:renametablefield
qgis:textattributes native:extractspecificvertices native:interpolatepoint native:linesubstring native:affinetransform native:projectpointcartesian
native:extenttolayer native:extractzvalues native:extractmvalues native:zonalstatistics native:rasterlayerproperties native:fuzzifyrasterlinearmembership
""".split()


def wait(ms):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def dump_modal():
    from qgis.PyQt.QtWidgets import QApplication, QComboBox, QListWidget

    w = QApplication.activeModalWidget()
    lines.append("modal: %s %s" % (w.metaObject().className() if w else None, w.objectName() if w else None))
    if w is None:
        return
    lw = w.findChild(QListWidget, "mOptionsListWidget")
    if lw is not None:
        lines.append("layer props pages: %s" % [lw.item(i).text() for i in range(lw.count())])
    for cb in w.findChildren(QComboBox):
        if cb.objectName() in ("cboRenderers", "mRendererTypeComboBox"):
            lines.append("renderer combo %s: %s" % (cb.objectName(), [(cb.itemText(i), cb.itemData(i)) for i in range(cb.count())]))
    for c in w.findChildren(QComboBox):
        if c.count() > 5 and "Single" in c.itemText(0):
            lines.append("combo %s: %s" % (c.objectName(), [c.itemText(i) for i in range(c.count())]))
    w.reject()


def run():
    import qgis.utils as utils
    from qgis.core import QgsApplication, QgsProject, QgsVectorLayer
    from qgis.PyQt.QtWidgets import QDockWidget, QToolBar
    from qgis.PyQt.QtGui import QAction

    win = utils.iface.mainWindow()
    try:
        wait(1500)
        tb = win.findChild(QToolBar, "mAnnotationsToolBar")
        if tb is not None:
            lines.append("annotations toolbar: %s" % [(a.objectName(), a.text()) for a in tb.actions()])
            for a in tb.actions():
                w = tb.widgetForAction(a)
                if w is not None and hasattr(w, "menu") and w.menu() is not None:
                    lines.append("  button menu: %s" % [(x.objectName(), x.text()) for x in w.menu().actions()])
        tb = win.findChild(QToolBar, "mSnappingToolBar")
        if tb is not None:
            lines.append("snapping toolbar: %s" % [(a.objectName(), a.text()) for a in tb.actions()])
        lines.append("docks: %s" % [(d.objectName(), d.windowTitle()) for d in win.findChildren(QDockWidget) if d.parent() is win])
        lines.append("locator action: %s" % [(a.objectName(), a.text()) for a in win.findChildren(QAction) if "ocator" in a.objectName() or "ocator" in a.text()])
        lines.append("annotation actions: %s" % [(a.objectName(), a.text()) for a in win.findChildren(QAction) if "nnotation" in a.text()])
        reg = QgsApplication.processingRegistry()
        missing = [a for a in ALGS if reg.algorithmById(a) is None]
        lines.append("missing algs: %s" % missing)
        lines.append("providers: %s" % [(p.id(), p.name(), len(p.algorithms())) for p in reg.providers()])
        lines.append("lrelease: %s" % [p for p in (r"C:\Program Files\QGIS 3.44.6\apps\Qt5\bin\lrelease.exe", r"C:\Program Files\QGIS 3.44.6\bin\lrelease.exe") if os.path.exists(p)])
        from qgis.gui import QgsGui
        sm = QgsGui.shortcutsManager()
        lines.append("shortcuts Z/X/C: %s" % [(k, sm.objectForSequence(__import__('qgis.PyQt.QtGui', fromlist=['QKeySequence']).QKeySequence(k))) for k in ("Z", "X", "C", "Ctrl+F")])
        # layer properties pages
        layer = QgsVectorLayer("Point?crs=EPSG:4326&field=name:string", "Probe", "memory")
        QgsProject.instance().addMapLayer(layer)
        QTimer.singleShot(2500, dump_modal)
        utils.iface.showLayerProperties(layer)
        wait(500)
        # recent projects
        from qgis.core import QgsSettings
        s = QgsSettings()
        s.beginGroup("UI/recentProjects")
        lines.append("recent groups: %s" % s.childGroups()[:5])
        for g in s.childGroups()[:3]:
            s.beginGroup(g)
            lines.append("  %s: %s" % (g, {k: s.value(k) for k in s.childKeys()}))
            s.endGroup()
        s.endGroup()
        lines.append("templates dir: %s" % s.value("qgis/projectTemplateDir"))
        from qgis.core import QgsNominatimGeocoder  # noqa: F401
        lines.append("nominatim geocoder OK")
        from qgis.gui import QgsDataSourceSelectDialog  # noqa: F401
        lines.append("QgsDataSourceSelectDialog OK")
        lines.append("renderer registry: %s" % [(r, QgsApplication.rendererRegistry().rendererMetadata(r).visibleName()) for r in QgsApplication.rendererRegistry().renderersList()])
    except Exception:
        lines.append(traceback.format_exc())
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    QgsProject.instance().setDirty(False)
    win.close()


QTimer.singleShot(800, run)
