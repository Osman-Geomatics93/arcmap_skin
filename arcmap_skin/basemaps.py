# -*- coding: utf-8 -*-
"""Add Basemap gallery: worldwide tile services that need no API key."""

from qgis.core import QgsLayerTreeLayer, QgsProject, QgsRasterLayer
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import QMenu

from .util import arcmap_icon, tr

# (title, xyz url template, zmax, attribution)
BASEMAPS = [
    ("OpenStreetMap", "https://tile.openstreetmap.org/{z}/{x}/{y}.png", 19, "© OpenStreetMap contributors"),
    ("OpenTopoMap", "https://a.tile.opentopomap.org/{z}/{x}/{y}.png", 17, "© OpenStreetMap contributors, SRTM | © OpenTopoMap (CC-BY-SA)"),
    ("Humanitarian (HOT)", "https://a.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png", 19, "© OpenStreetMap contributors, HOT"),
    ("CartoDB Positron (Light Gray Canvas)", "https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png", 19, "© OpenStreetMap contributors © CARTO"),
    ("CartoDB Dark Matter (Dark Gray Canvas)", "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png", 19, "© OpenStreetMap contributors © CARTO"),
    ("Esri World Imagery", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", 19, "Esri, Maxar, Earthstar Geographics, and the GIS User Community"),
    ("Esri World Street Map", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}", 19, "Esri, HERE, Garmin, USGS, Intermap, INCREMENT P, NRCan, Esri Japan, METI, Esri China (Hong Kong), NOSTRA, © OpenStreetMap contributors, and the GIS User Community"),
    ("Esri World Topographic Map", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}", 19, "Esri, HERE, Garmin, Intermap, increment P Corp., GEBCO, USGS, FAO, NPS, NRCAN, GeoBase, IGN, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China (Hong Kong), (c) OpenStreetMap contributors, and the GIS User Community"),
    ("Esri Terrain with Labels", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}", 13, "Esri, USGS, NOAA"),
    ("Esri Shaded Relief", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}", 13, "Esri, USGS"),
    ("Esri Ocean Basemap", "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}", 13, "Esri, GEBCO, NOAA, National Geographic, DeLorme, HERE, Geonames.org, and other contributors"),
    ("Esri National Geographic", "https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}", 16, "National Geographic, Esri, DeLorme, HERE, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, increment P Corp."),
    ("Esri Light Gray Canvas", "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", 16, "Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community"),
    ("Esri Dark Gray Canvas", "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}", 16, "Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community"),
]


def add_basemap(iface, title, url, zmax, attribution):
    uri = "type=xyz&url=%s&zmax=%d&zmin=0" % (url.replace("&", "%26"), zmax)
    layer = QgsRasterLayer(uri, title, "wms")
    if not layer.isValid():
        iface.messageBar().pushWarning(tr("Add Basemap"), tr("Could not add %s") % title)
        return None
    md = layer.metadata()
    md.setRights([attribution])
    layer.setMetadata(md)
    project = QgsProject.instance()
    project.addMapLayer(layer, False)
    root = project.layerTreeRoot()
    root.insertChildNode(-1, QgsLayerTreeLayer(layer))  # basemaps go to the bottom
    return layer


def basemap_menu(iface, parent):
    menu = QMenu(tr("Add Basemap"), parent)
    menu.setObjectName("ArcMapBasemapMenu")
    menu.setIcon(arcmap_icon("basemap"))
    for title, url, zmax, attribution in BASEMAPS:
        action = QAction(arcmap_icon("basemap"), title, menu)
        action.triggered.connect(lambda _=False, t=title, u=url, z=zmax, a=attribution: add_basemap(iface, t, u, z, a))
        menu.addAction(action)
    return menu
