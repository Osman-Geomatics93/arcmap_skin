# Where is it? ArcMap → QGIS with ArcMap Skin

| In ArcMap | With ArcMap Skin | Behind the scenes (QGIS) |
|---|---|---|
| File ▸ Add Data… | File ▸ Add Data…, Standard toolbar Add Data ▾ | Browser-based data source select dialog; Data Source Manager in the dropdown |
| Add Basemap | File ▸ Add Basemap ▸, Add Data ▾ | XYZ tile layers (OSM, OpenTopoMap, CartoDB, Esri services) |
| Table Of Contents, List By | Table Of Contents pane, four List By buttons | Layers panel; Source/Visibility/Selection views are the plugin's |
| Catalog window | Catalog pane (Contents / Preview tabs, Connect To Folder) | Browser panel |
| ArcToolbox | ArcToolbox pane (ArcMap toolboxes) | Every Processing algorithm, filed by provider and group |
| Search window | Search pane, Geoprocessing ▸ Search For Tools | Processing Toolbox with its search box |
| Select By Attributes | Selection ▸ Select By Attributes…, Tools toolbar | Query Builder dialog → `selectByExpression` |
| Definition Query | Layer Properties ▸ Definition Query, TOC right-click | Query Builder → layer subset string |
| Select By Location | Selection ▸ Select By Location… | Processing *Select by location* |
| Identify | Tools toolbar Identify, "Identify from:" selector | Identify tool and Identify Results panel |
| Find | Tools toolbar Find, Windows ▸ Find | Plugin Find window (attributes + Nominatim) |
| Go To XY | Tools toolbar | Plugin dialog, centres the map |
| Measure | Tools toolbar Measure ▾ | Measure window; QGIS measure tools for line/area |
| Editor toolbar ▸ Start Editing | Editor ▾ ▸ Start Editing | Layer picker + `startEditing()` |
| Edit Tool | Editor toolbar, first button | Plugin map tool: select, drag to move, double-click vertices |
| Create Features | Editor toolbar / Windows menu | Plugin pane over Add Feature + construction tools |
| Attributes window | Editor toolbar / Windows menu | Plugin pane over QgsAttributeForm |
| Snapping toolbar | Customize ▸ Toolbars ▸ Snapping | Project snapping configuration |
| Table window | Open Attribute Table | QGIS attribute table with ArcMap toolbar, menus and footer |
| Label Manager | Labeling toolbar, Windows menu | Plugin pane; layer labelling on/off |
| Layer Properties tabs | General, Source, Display, Symbology, Fields, Definition Query, Labels, Joins & Relates, Time, HTML Popup, More | QGIS layer properties pages |
| Data Frame Properties | View ▸ Data Frame Properties…, map right-click | Project properties with ArcMap tabs |
| ArcMap Options | Customize ▸ ArcMap Options… | QGIS Options with ArcMap tabs; the ArcMap Skin page holds the feature switches |
| Customize Mode | Customize ▸ Customize Mode… | Plugin Customize dialog (toolbars, commands, options) |
| Layout View | Data View / Layout View buttons, View menu | Layout designer with Insert menu and Layout toolbar |
| Export Map | File ▸ Export Map… | Export map to image / PDF |
| Bookmarks | Bookmarks menu | Spatial bookmarks |
| Magnifier / Viewer | Windows menu | Plugin magnifier; new map view |
| Save As Layer File (.lyr) | TOC right-click ▸ Save As Layer File… | Layer definition file (.qlr) |
| Map document (.mxd) | Project (.qgz) | .mxd files cannot be opened by QGIS |
