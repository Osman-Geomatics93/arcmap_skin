# -*- coding: utf-8 -*-
"""ArcMap's Layout View inside the QGIS layout designer.

Each designer window that opens while the look is on gets:

* an **Insert** menu with ArcMap's wording (Data Frame, Title, Text, Dynamic
  Text, Neatline, Legend, North Arrow, Scale Bar, Picture, Table, HTML),
* a **Layout** toolbar (Zoom In/Out, Pan, Zoom Whole Page, Zoom to 100 %,
  Zoom to Page Width, Change Layout, Page and Print Setup, Print, Export,
  Focus Data Frame),
* ArcMap captions on the designer's own menus and a "- Layout View" title.

All changes are recorded per designer and undone when the look goes off.
"""

from qgis.PyQt.QtCore import QObject, QSize, Qt
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import QMenu, QToolBar

from .util import Changes, alive, arcmap_icon, tr

# ArcMap Insert menu: (QGIS action text in the Add Item menu, ArcMap caption, icon)
INSERT_ITEMS = [
    ("Add Map", "Data Frame", "data_view"),
    ("Add Label", "Title", "title"),
    ("Add Label", "Text", "text"),
    ("Add Dynamic Text", "Dynamic Text", "text"),
    ("Add Shape", "Neatline", "grid"),
    None,
    ("Add Legend", "Legend", "toc"),
    ("Add North Arrow", "North Arrow", "north_arrow"),
    ("Add Scale Bar", "Scale Bar", "scale_bar"),
    None,
    ("Add Picture", "Picture", "picture"),
    ("Add Attribute Table", "Table", "table"),
    ("Add HTML", "HTML", "html_popup"),
    ("Add Elevation Profile", "Elevation Profile", "statistics"),
]

# ArcMap Layout toolbar: (QGIS action objectName, caption, icon)
LAYOUT_TOOLBAR = [
    ("mActionZoomIn", "Zoom In", "fixed_zoom_in"),
    ("mActionZoomOut", "Zoom Out", "fixed_zoom_out"),
    ("mActionPan", "Pan", "pan"),
    ("mActionZoomTool", "Zoom", "zoom_in"),
    ("mActionZoomAll", "Zoom Whole Page", "full_extent"),
    ("mActionZoomActual", "Zoom to 100%", "zoom_layer"),
    ("mActionZoomToWidth", "Zoom to Page Width", "layout_view"),
    None,
    ("mActionLoadFromTemplate", "Change Layout…", "layout_view"),
    ("mActionPageSetup", "Page and Print Setup…", "page_setup"),
    ("mActionPrint", "Print…", "print"),
    ("mActionExportAsPDF", "Export Map…", "export_map"),
    None,
    ("mActionSelectMoveItem", "Select Elements", "select_elements"),
    ("mActionMoveItemContent", "Focus Data Frame", "pan_selected"),
    ("mActionLayoutProperties", "Layout Properties…", "properties"),
]

MENU_CAPTIONS = {
    "mLayoutMenu": "File",
    "menuEdit": "Edit",
    "mMenuView": "View",
    "menuLayout": "Items",
    "mItemMenu": "Add Item (QGIS)",
}


def _find_text_action(menu, text):
    for a in menu.actions():
        if a.text().replace("&", "") == text:
            return a
    return None


class DesignerDresser(QObject):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.designers = {}  # window → Changes
        iface.layoutDesignerOpened.connect(self.dress)
        iface.layoutDesignerWillBeClosed.connect(self.forget)
        for designer in iface.openLayoutDesigners():
            self.dress(designer)

    def dress(self, designer):
        win = designer.window()
        if win is None or win in self.designers:
            return
        changes = Changes()
        self.designers[win] = changes
        bar = win.menuBar()
        # ArcMap captions on the designer's menus
        for act in bar.actions():
            menu = act.menu()
            if menu is not None and menu.objectName() in MENU_CAPTIONS:
                changes.set(act, "text", tr(MENU_CAPTIONS[menu.objectName()]))
        item_menu = win.findChild(QMenu, "mItemMenu")
        # Insert menu
        insert = QMenu(tr("Insert"), bar)
        insert.setObjectName("ArcMapLayoutInsertMenu")
        if item_menu is not None:
            for entry in INSERT_ITEMS:
                if entry is None:
                    insert.addSeparator()
                    continue
                qgis_text, caption, icon = entry
                source = _find_text_action(item_menu, qgis_text)
                if source is None:
                    continue
                proxy = insert.addAction(arcmap_icon(icon), tr(caption))
                proxy.triggered.connect(source.trigger)
        view_menu = win.findChild(QMenu, "mMenuView")
        before = view_menu.menuAction() if view_menu is not None else None
        if insert.actions():
            if before is not None:
                bar.insertMenu(before, insert)
            else:
                bar.addMenu(insert)
        # Layout toolbar
        toolbar = QToolBar(tr("Layout"), win)
        toolbar.setObjectName("ArcMapLayoutViewToolBar")
        toolbar.setIconSize(QSize(18, 18))
        pending = False
        for entry in LAYOUT_TOOLBAR:
            if entry is None:
                pending = bool(toolbar.actions())
                continue
            name, caption, icon = entry
            action = win.findChild(QAction, name)
            if action is None:
                continue
            if pending:
                toolbar.addSeparator()
                pending = False
            changes.set(action, "icon", arcmap_icon(icon))
            changes.set(action, "toolTip", tr(caption))
            toolbar.addAction(action)
        win.addToolBarBreak(Qt.ToolBarArea.TopToolBarArea)
        win.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        for name in ("mNavigationToolbar",):
            tb = win.findChild(QToolBar, name)
            if tb is not None:
                changes.set(tb, "visible", False)
        changes.set(win, "windowTitle", "%s - %s" % (designer.layout().name() if designer.layout() else "", tr("Layout View")))

        def undo(bar=bar, insert=insert, toolbar=toolbar, win=win):
            if alive(bar) and alive(insert):
                bar.removeAction(insert.menuAction())
                insert.setParent(None)
                insert.deleteLater()
            if alive(win) and alive(toolbar):
                win.removeToolBar(toolbar)
                toolbar.setParent(None)
                toolbar.deleteLater()

        changes.add(undo)

    def forget(self):
        for win in list(self.designers):
            if not alive(win) or not win.isVisible():
                self.designers.pop(win, None)

    def stop(self):
        try:
            self.iface.layoutDesignerOpened.disconnect(self.dress)
            self.iface.layoutDesignerWillBeClosed.disconnect(self.forget)
        except (TypeError, RuntimeError):
            pass
        for win, changes in list(self.designers.items()):
            if alive(win):
                try:
                    changes.undo()
                except Exception as exc:  # noqa: BLE001
                    from .util import log_ignored

                    log_ignored("layout designer undo", exc)
        self.designers = {}


def install_layout_designer(iface, changes):
    dresser = DesignerDresser(iface)
    changes.add(dresser.stop)
    return dresser
