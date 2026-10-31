# ArcMap Skin for QGIS

ArcMap Skin gives QGIS the look and layout of **ArcMap 10**, drawn flat and
modern: the classic menu bar, dockable Standard / Tools / Editor toolbars,
a Table Of Contents with *List By* views, Catalog, Search and ArcToolbox
panes, Data View / Layout View buttons, an ArcMap-style status bar and
attribute table, ArcMap symbology defaults and a redrawn icon theme.

One click switches the look on; one click switches it off and QGIS comes
back exactly as it was. Every change the plugin makes is recorded and
replayed in reverse.

ArcMap Skin is an independent project. It is **not affiliated with,
sponsored or endorsed by Esri**. All icons are original artwork or derived
from QGIS's own icons (GPL).

## What changes

| Area | ArcMap Skin |
|---|---|
| Menu bar | File, Edit, View, Bookmarks, Insert, Selection, Geoprocessing, Customize, Windows, Help – built from QGIS's own commands. QGIS's menus stay available under *Customize ▸ QGIS Menus*. |
| Toolbars | Standard (New, Open, Save, Print, Cut/Copy/Paste, Undo/Redo, Add Data ▾, Scale, Editor Toolbar, TOC, Catalog, Search, ArcToolbox, Python, ModelBuilder), Tools (Zoom, Pan, Full Extent, Fixed Zoom, Back/Forward, Select Features ▾, Clear Selected, Select Elements, Identify, HTML Popup, Measure ▾, Find, Go To XY, Time Slider, Viewer Window), Editor (Editor ▾, Edit Tool, Construction Tools ▾, Trace, Edit Vertices, Reshape, Cut Polygons, Split, Rotate, Attributes, Sketch Properties, Create Features), Layout, Georeferencing, 3D Analyst. QGIS's Snapping, Labeling, Selection, Raster, Annotations toolbars keep their widgets and get ArcMap titles. |
| Table Of Contents | List By Drawing Order (QGIS layer tree), Source, Visibility and Selection views. |
| Panes | Catalog (Browser), ArcToolbox (Processing Toolbox), Symbology (Layer Styling) tabbed on the right; the active pane gets ArcMap's blue title. |
| Map frame | Data View / Layout View buttons under the map; ArcMap status bar with message area, selection count, Pause Drawing, CRS button and an `x y Units` coordinate readout. |
| Attribute table | ArcMap's Table window: *Table Options ▾* (Find and Replace, Select By Attributes, Add Field, Turn All Fields On, Arrange Fields, Joins and Relates, Export, Reload Cache…), ArcMap toolbar order, field-header menu (Sort, Summarize, Statistics, Field Calculator, Calculate Geometry, Turn Field Off, Delete Field, Properties), row menu (Flash, Zoom To, Pan To, Identify, Select/Unselect, Copy, Delete), cyan selection, record navigator with Show All / Selected and *(n out of m Selected)*, tables docked in one tabbed window. |
| Symbology | Pastel random fills with a grey outline, cyan selection, Arial 10 labels, ~40 ArcMap-style colour ramps tagged "ArcMap". |
| Icons | A complete QGIS icon theme in the ArcMap palette plus 140 hand-drawn toolbar icons. |
| Query Builder | ArcMap-style *Select By Attributes* (new / add / remove / select from current) and layer *Definition Query*, with fields, operators, Get Unique Values, Verify, Load/Save. |
| ArcToolbox | Every Processing algorithm (QGIS, GDAL, GRASS, PDAL, models, scripts) filed into ArcMap's toolboxes and toolsets (Analysis, Cartography, Conversion, Data Management, Editing, Spatial Analyst, 3D Analyst, Network Analyst, Spatial Statistics, My Toolboxes): the well-known tools under their ArcMap names (Clip, Erase, Intersect, Union, Buffer, Near, Dissolve, Project, Slope…), the rest by provider and group, with Search For Tools, Batch and Tool Help. |
| TOC menu | ArcMap right-click menu on layers and groups (Open Attribute Table, Joins and Relates, Zoom To Layer, Visible Scale Range, Selection, Label Features, Edit Features, Definition Query, Data, Save As Layer File, Properties) with the QGIS menu kept underneath. |
| Layer Properties | ArcMap layout: tabs across the top in ArcMap's order (General, Source, Display, Symbology, Fields, Definition Query, Labels, Joins & Relates, Time, HTML Popup; raster: General, Source, Key Metadata, Display, Transparency, Symbology, Time), QGIS-only pages under a *More* tab, Definition Query opening the Query Builder, and ArcMap renderer wording (Categories – Unique values, Quantities – Graduated colors…). |
| Add Data | ArcMap-style single-tree Add Data dialog, *Connect To Folder* in Catalog, and an *Add Basemap* gallery (OSM, OpenTopoMap, CartoDB, Esri services, no API keys). |
| Find | Find window with *Features* (attribute search across layers) and *Locations* (Nominatim geocoding) tabs. |
| Editing | Start Editing / Stop Editing / Save Edits in ArcMap wording, a *Create Features* window with feature templates and construction tools, and an ArcMap *Snapping* toolbar (Vertex, End, Edge, Midpoint, Intersection). |
| Draw toolbar | Select Elements, New Polygon / Line / Marker / Text / Picture on QGIS annotation tools. |
| Shortcuts | Z zoom in, X zoom out, C pan, S select, I identify; ArcMap scale list in the scale box; display-units menu (map units, decimal degrees, DMS, DDM) on the coordinate readout. |
| Getting Started | ArcMap's start-up dialog with Existing Maps (recent, browse) and New Maps (blank, templates). |
| Edit Tool | ArcMap's black-arrow Edit Tool: click to select, drag to move, double-click for vertex editing, right-click menu (Move…, Rotate, Edit Vertices, Attributes…, Copy, Paste, Delete, Unselect All). |
| Attributes window | Selected features of the layers being edited on the left, editable form on the right. |
| Label Manager | Layers with label on/off check boxes and Properties, plus a Labeling toolbar with Pause Labeling, View Unplaced Labels and QGIS's label tools. |
| Symbology tab | ArcMap's "Show:" tree (Features, Categories, Quantities, Charts, Multiple Attributes) beside the renderer page, with Add All Values / Add Values / Remove wording. |
| Data Frame Properties, Options | ArcMap tabs on the project properties and options dialogs, other pages under More. |
| Map right-click | Zoom In/Out, Full Extent, Previous/Next Extent, Go To XY, Add Data, Pause Drawing, Data Frame Properties. |
| Identify | "Identify from:" selector (top-most, visible, selectable, current layer, choose layers) on the Identify pane. |
| Measure window | Line, Area and Feature measuring with a units menu and running totals. |
| Magnifier | Floating magnifier following the mouse at 200–1000 %. |
| Customize dialog | Toolbars (show/hide), Commands (find any command, add it to a toolbar, run it), Options (start-up behaviour, large icons, keyboard, interface customization). |
| Status bar | "Drawing…" indicator, task progress bar and a running-tasks button, which the hidden QGIS status bar used to provide. |
| Languages | English and Arabic (`scripts/i18n.py` builds the `.qm` without Qt tools). |

## Requirements

* QGIS 3.40 or newer (Qt 5) or QGIS 4.x (Qt 6).

## Installation

**From ZIP** – download `arcmap_skin-<version>.zip` from the releases page,
then *Plugins ▸ Manage and Install Plugins ▸ Install from ZIP*. The look is
applied as soon as the plugin loads.

**Switching** – *Customize ▸ ArcMap look* or *Plugins ▸ ArcMap Skin ▸ ArcMap
look*. While the plugin is enabled the look is applied at every QGIS start.
Layer icons in the Table Of Contents and Catalog finish changing after one
restart (QGIS caches them at start-up).

## Development

```
git clone https://github.com/Osman-Geomatics93/arcmap_skin.git && cd arcmap_skin
python scripts/draw_icons.py                                   # hand-drawn icons
"C:/Program Files/QGIS 3.44.6/bin/python-qgis.bat" scripts/build_icon_theme.py   # derived icon theme
python scripts/dev_link.py                                     # junction into the default profile
"C:/Program Files/QGIS 3.44.6/bin/python-qgis.bat" -m unittest discover -s tests -v
"C:/Program Files/QGIS 3.44.6/bin/python-qgis.bat" scripts/i18n.py ar          # rebuild translations
python scripts/package.py                                      # dist/arcmap_skin-<version>.zip
```

In QGIS, enable **ArcMap Skin** in the plugin manager and use *Plugin
Reloader* while developing. Automated runs use a separate profile store so
your own QGIS profile is never touched:

```
python scripts/dev_link.py --profiles-path=D:\QGIS_Plugins\Arcmap_Skin\.qgis_profiles
"C:/Program Files/QGIS 3.44.6/bin/qgis-bin.exe" --profiles-path D:\QGIS_Plugins\Arcmap_Skin\.qgis_profiles --code tests/run_smoke.py
``` `tests/smoke_in_qgis.py` can be run from the
Python console to check the on/off round trip and that every core QGIS
toolbar action is reachable from the ArcMap interface. `scripts/dump_names.py`
prints the objectNames of toolbars, menus and docks of the running QGIS,
which is what the specs in `menus.py`, `toolbars.py` and `panes.py` rely on.

### Layout of the code

| Module | Role |
|---|---|
| `plugin.py` | on/off switch, ordered skin steps, saved window state |
| `util.py` | `Changes` undo log, icon helpers, widget lookup |
| `stylesheet.py` | marked QSS block at the front of the application stylesheet |
| `icon_theme.py` | install/activate the icon theme, swap live icons |
| `menus.py`, `toolbars.py` | ArcMap menu bar and toolbars from QGIS actions |
| `actions.py` | ArcMap-only commands (Go To XY, Buffer…, Search For Tools…) |
| `panes.py`, `contents_views.py` | pane titles/arrangement, Table Of Contents List By views |
| `mapview.py` | view buttons and the ArcMap status bar |
| `dialogs.py`, `attribute_table.py` | window dresser; ArcMap Table window (toolbar, Table Options, context menus, footer, Find and Replace) |
| `symbology.py` | default symbols, selection colour, label font, colour ramps |
| `query_builder.py` | Select By Attributes / Definition Query dialog |
| `arctoolbox.py` | ArcToolbox dock and the toolbox → algorithm map |
| `toc_menu.py` | ArcMap context menu for the Table Of Contents |
| `basemaps.py`, `find.py`, `editing.py`, `shortcuts.py`, `getting_started.py` | basemap gallery, Find window, editing workflow and snapping toolbar, keyboard shortcuts, start-up dialog |
| `edit_tool.py`, `attributes_window.py`, `label_manager.py`, `measure.py`, `magnifier.py`, `customize.py`, `canvas_menu.py` | Edit Tool, Attributes window, Label Manager, Measure and Magnifier windows, Customize dialog, map right-click menu |

## Licence

GPL-2.0-or-later. The derived icon theme is built from QGIS icons under the
same licence.
