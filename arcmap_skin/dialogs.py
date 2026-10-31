# -*- coding: utf-8 -*-
"""ArcMap-style attribute table and icons in other windows.

:class:`WindowDresser` listens for window focus changes. Each new
attribute table (``QgsAttributeTableDialog/<layer id>``) gets its toolbar
rebuilt in ArcMap's order behind a *Table Options* button, and an ArcMap
record navigator footer. Everything is undone through ``Changes``.
"""

from qgis.PyQt.QtCore import QObject, Qt, QTimer
from qgis.PyQt.QtGui import QGuiApplication
from qgis.PyQt.QtWidgets import QApplication, QDialog, QMenu, QWidget

from .util import alive, tr

from .attribute_table import TABLE_DONE, dress_attribute_table  # noqa: F401


# QGIS layer-properties page → ArcMap tab name
LAYER_PAGES = {
    "Information": "General",
    "Source": "Source",
    "Symbology": "Symbology",
    "Labels": "Labels",
    "Fields": "Fields",
    "Attributes Form": "Fields Form",
    "Joins": "Joins & Relates",
    "Display": "HTML Popup",
    "Rendering": "Display",
    "Temporal": "Time",
    "Metadata": "Item Description",
    "Transparency": "Display",
}

# QGIS renderer id → ArcMap symbology wording
RENDERERS = {
    "nullSymbol": "Features – No symbols",
    "singleSymbol": "Features – Single symbol",
    "categorizedSymbol": "Categories – Unique values",
    "graduatedSymbol": "Quantities – Graduated colors",
    "RuleRenderer": "Rule-based",
    "pointDisplacement": "Multiple attributes – Point displacement",
    "pointCluster": "Multiple attributes – Point cluster",
    "heatmapRenderer": "Quantities – Density (heatmap)",
    "embeddedSymbol": "Embedded symbols",
    "mergedFeatureRenderer": "Merged features",
    "invertedPolygonRenderer": "Inverted polygons",
    "25dRenderer": "2.5 D",
}

PAGES_DONE = "arcmapPagesDone"

# ArcMap Layer Properties tabs → QGIS page (by its original title); None = special
VECTOR_TABS = [
    ("General", "Information"),
    ("Source", "Source"),
    ("Display", "Rendering"),
    ("Symbology", "Symbology"),
    ("Fields", "Fields"),
    ("Definition Query", None),
    ("Labels", "Labels"),
    ("Joins & Relates", "Joins"),
    ("Time", "Temporal"),
    ("HTML Popup", "Display"),
]
RASTER_TABS = [
    ("General", "Information"),
    ("Source", "Source"),
    ("Key Metadata", "Metadata"),
    ("Display", "Rendering"),
    ("Transparency", "Transparency"),
    ("Symbology", "Symbology"),
    ("Time", "Temporal"),
]
# Data Frame Properties (QGIS project properties)
PROJECT_TABS = [
    ("General", "General"),
    ("Data Frame", "View Settings"),
    ("Coordinate System", "CRS"),
    ("Time", "Temporal"),
    ("Metadata", "Metadata"),
    ("Default Styles", "Default Styles"),
]
# ArcMap Options (QGIS options: pages addressed by widget objectName, the
# options dialog uses a tree rather than the page list)
OPTIONS_TABS = [
    ("General", "mOptionsPageGeneral"),
    ("Data View", "mOptionsPageMapCanvas"),
    ("Display", "mOptionsPageRendering"),
    ("Tools", "mOptionsPageMapTools"),
    ("Editing", "mOptionsPageDigitizing"),
    ("Layout View", "mOptionsPageComposer"),
    ("Coordinate System", "mOptionsPageCRS"),
    ("Data Sources", "mOptionsPageDataSources"),
    ("Colors", "mOptionsPageColors"),
    ("Fonts", "mOptionsPageFonts"),
    ("ArcMap Skin", "mOptionsPageArcMapSkin"),
]
TABS_BY_CLASS = {
    "QgsVectorLayerProperties": VECTOR_TABS,
    "QgsRasterLayerProperties": RASTER_TABS,
    "QgsProjectProperties": PROJECT_TABS,
    "QgsOptions": OPTIONS_TABS,
}

# ArcMap Symbology "Show:" tree → QGIS renderer id (or ("page", title))
SYMBOLOGY_TREE = [
    ("Features", [("Single symbol", "singleSymbol"), ("No symbols", "nullSymbol")]),
    ("Categories", [("Unique values", "categorizedSymbol"), ("Unique values, many fields", "categorizedSymbol"),
                    ("Match to symbols in a style", "categorizedSymbol")]),
    ("Quantities", [("Graduated colors", "graduatedSymbol"), ("Graduated symbols", "graduatedSymbol"),
                    ("Proportional symbols", "graduatedSymbol"), ("Density (heatmap)", "heatmapRenderer")]),
    ("Charts", [("Pie", ("page", "Diagrams")), ("Bar/Column", ("page", "Diagrams")), ("Stacked", ("page", "Diagrams"))]),
    ("Multiple Attributes", [("Quantity by category (rule-based)", "RuleRenderer"), ("Point displacement", "pointDisplacement"),
                             ("Point cluster", "pointCluster"), ("Inverted polygons", "invertedPolygonRenderer"),
                             ("Merged features", "mergedFeatureRenderer"), ("2.5 D", "25dRenderer"),
                             ("Embedded symbols", "embeddedSymbol")]),
]

# QGIS button text → ArcMap wording in the categorized / graduated pages
SYMBOLOGY_BUTTONS = {
    "btnAddCategories": "Add All Values",
    "btnAddCategory": "Add Values…",
    "btnDeleteCategories": "Remove",
    "btnDeleteAllCategories": "Remove All",
    "btnGraduatedClassify": "Classify…",
    "btnGraduatedAdd": "Add Class",
    "btnGraduatedDelete": "Remove",
    "btnDeleteAllClasses": "Remove All",
}


class ArcMapPropertyTabs(QWidget):
    """ArcMap-style tab row driving QGIS's page list (which stays hidden)."""

    def __init__(self, dialog, list_widget, stack, tabs, iface):
        super().__init__(dialog)
        from qgis.PyQt.QtWidgets import QHBoxLayout, QTabBar

        self.setObjectName("ArcMapPropertyTabs")
        self.dialog = dialog
        self.list = list_widget
        self.stack = stack
        self.iface = iface
        self._syncing = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.bar = QTabBar(self)
        self.bar.setObjectName("ArcMapPropertyTabBar")
        self.bar.setExpanding(False)
        self.bar.setDrawBase(True)
        self.bar.setUsesScrollButtons(True)
        self.rows = []  # tab index → list row (None = Definition Query)
        titles = {list_widget.item(i).data(Qt.ItemDataRole.UserRole + 42) or list_widget.item(i).text(): i
                  for i in range(list_widget.count())}
        self.used_rows = set()
        for caption, qgis_title in tabs:
            if qgis_title is None:
                self.bar.addTab(tr(caption).replace("&", "&&"))
                self.rows.append(None)
            elif qgis_title in titles:
                self.bar.addTab(tr(caption).replace("&", "&&"))
                self.rows.append(titles[qgis_title])
                self.used_rows.add(titles[qgis_title])
        # everything else under "More"
        self.more_index = self.bar.addTab(tr("More"))
        self.rows.append("more")
        layout.addWidget(self.bar, 1)
        self.more_menu = QMenu(self)
        for i in range(list_widget.count()):
            if i in self.used_rows:
                continue
            action = self.more_menu.addAction(list_widget.item(i).icon(), list_widget.item(i).text())
            action.setData(i)
        self.more_menu.triggered.connect(self._more_picked)
        self.bar.currentChanged.connect(self._tab_changed)
        self.bar.tabBarClicked.connect(self._tab_clicked)
        list_widget.currentRowChanged.connect(self._row_changed)
        self._row_changed(list_widget.currentRow())

    def _tab_clicked(self, index):
        if index == self.more_index:
            rect = self.bar.tabRect(index)
            QTimer.singleShot(0, lambda: self.more_menu.exec(self.bar.mapToGlobal(rect.bottomLeft())))
        elif self.rows[index] is None:
            QTimer.singleShot(0, self._definition_query)

    def _tab_changed(self, index):
        if self._syncing or index < 0:
            return
        row = self.rows[index]
        if isinstance(row, int):
            self._syncing = True
            self.list.setCurrentRow(row)
            self._syncing = False
        elif row is None or row == "more":
            # Definition Query / More: keep the page that was showing
            QTimer.singleShot(0, lambda: self._row_changed(self.list.currentRow()))

    def _row_changed(self, row):
        if self._syncing or row < 0:
            return
        self._syncing = True
        if row in self.rows:
            self.bar.setCurrentIndex(self.rows.index(row))
            self.bar.setTabText(self.more_index, tr("More"))
        else:
            self.bar.setTabText(self.more_index, self.list.item(row).text() if self.list.item(row) else tr("More"))
            self.bar.setCurrentIndex(self.more_index)
        self._syncing = False

    def _more_picked(self, action):
        row = action.data()
        if isinstance(row, int):
            self.list.setCurrentRow(row)

    def _definition_query(self):
        layer = _layer_of_properties(self.dialog)
        if layer is not None:
            from .query_builder import open_definition_query

            open_definition_query(self.iface, layer)

    def remove(self):
        if not alive(self):  # the dialog was closed and deleted already
            return
        try:
            self.list.currentRowChanged.disconnect(self._row_changed)
        except (TypeError, RuntimeError):
            pass
        self.hide()
        self.setParent(None)
        self.deleteLater()


class OptionsTabs(QWidget):
    """ArcMap tab row for dialogs that use QGIS's options *tree* (QgsOptions):
    tabs address pages by objectName through QgsOptionsDialogBase."""

    def __init__(self, dialog, stack, tabs):
        super().__init__(dialog)
        from qgis.gui import QgsOptionsDialogBase
        from qgis.PyQt import sip
        from qgis.PyQt.QtWidgets import QHBoxLayout, QTabBar

        self.setObjectName("ArcMapPropertyTabs")
        self.stack = stack
        self.base = sip.cast(dialog, QgsOptionsDialogBase)
        self._syncing = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.bar = QTabBar(self)
        self.bar.setObjectName("ArcMapPropertyTabBar")
        self.bar.setExpanding(False)
        self.bar.setUsesScrollButtons(True)
        self.pages = []  # tab index → page objectName
        used = set()
        for caption, name in tabs:
            if stack.findChild(QWidget, name) is not None:
                self.bar.addTab(tr(caption).replace("&", "&&"))
                self.pages.append(name)
                used.add(name)
        self.more_index = self.bar.addTab(tr("More"))
        self.pages.append("more")
        layout.addWidget(self.bar, 1)
        self.more_menu = QMenu(self)
        for i in range(stack.count()):
            page = stack.widget(i)
            name = page.objectName()
            if name in used or not name:
                continue
            title = page.windowTitle() or name.replace("mOptionsPage", "").replace("mOptsPage_", "")
            action = self.more_menu.addAction(title)
            action.setData(name)
        self.more_menu.triggered.connect(lambda a: self._go(a.data()))
        self.bar.currentChanged.connect(self._tab_changed)
        self.bar.tabBarClicked.connect(self._tab_clicked)
        stack.currentChanged.connect(self._page_changed)
        self._page_changed(stack.currentIndex())

    def _go(self, name):
        if self.base is not None and name:
            self.base.setCurrentPage(name)

    def _tab_clicked(self, index):
        if index == self.more_index:
            rect = self.bar.tabRect(index)
            QTimer.singleShot(0, lambda: self.more_menu.exec(self.bar.mapToGlobal(rect.bottomLeft())))

    def _tab_changed(self, index):
        if self._syncing or index < 0:
            return
        name = self.pages[index]
        if name != "more":
            self._go(name)
        else:
            QTimer.singleShot(0, lambda: self._page_changed(self.stack.currentIndex()))

    def _page_changed(self, index):
        if self._syncing or index < 0:
            return
        page = self.stack.widget(index)
        name = page.objectName() if page else ""
        self._syncing = True
        if name in self.pages:
            self.bar.setCurrentIndex(self.pages.index(name))
            self.bar.setTabText(self.more_index, tr("More"))
        else:
            self.bar.setTabText(self.more_index, (page.windowTitle() if page else "") or name.replace("mOptionsPage", "") or tr("More"))
            self.bar.setCurrentIndex(self.more_index)
        self._syncing = False

    def remove(self):
        if not alive(self):  # the dialog was closed and deleted already
            return
        try:
            self.stack.currentChanged.disconnect(self._page_changed)
        except (TypeError, RuntimeError):
            pass
        self.hide()
        self.setParent(None)
        self.deleteLater()


def _layer_of_properties(dialog):
    """The layer a QGIS layer-properties dialog edits (from its title)."""
    from qgis.core import QgsProject

    title = dialog.windowTitle()
    # "Layer Properties - <name> — <page>"
    name = title.split(" - ", 1)[1] if " - " in title else ""
    for sep in (" \u2014 ", " — "):
        if sep in name:
            name = name.split(sep)[0]
    for layer in QgsProject.instance().mapLayers().values():
        if layer.name() == name.strip():
            return layer
    return None


def dress_layer_properties(changes, dialog, iface=None):
    """ArcMap layout for the layer properties dialog: tabs on top."""
    from qgis.PyQt.QtWidgets import QFrame, QListWidget, QStackedWidget

    if dialog.property(PAGES_DONE):
        return
    lw = dialog.findChild(QListWidget, "mOptionsListWidget")
    stack = dialog.findChild(QStackedWidget, "mOptionsStackedWidget")
    frame = dialog.findChild(QFrame, "mOptionsFrame")
    list_frame = dialog.findChild(QFrame, "mOptionsListFrame")
    if stack is None or frame is None or frame.layout() is None:
        return
    if lw is None:
        # tree-based options dialog (QgsOptions)
        if dialog.metaObject().className() != "QgsOptions":
            return
        dialog.setProperty(PAGES_DONE, True)
        widget = OptionsTabs(dialog, stack, OPTIONS_TABS)
        frame.layout().insertWidget(0, widget)
        if list_frame is not None:
            changes.set(list_frame, "visible", False)
        changes.add(widget.remove)
        return
    dialog.setProperty(PAGES_DONE, True)
    # remember the QGIS titles, then show ArcMap names in the (hidden) list / More menu
    for i in range(lw.count()):
        item = lw.item(i)
        item.setData(Qt.ItemDataRole.UserRole + 42, item.text())
        new = LAYER_PAGES.get(item.text())
        if new:
            item.setText(tr(new))
    if iface is None:
        from qgis.utils import iface as _iface

        iface = _iface
    tabs = TABS_BY_CLASS.get(dialog.metaObject().className(), VECTOR_TABS)
    widget = ArcMapPropertyTabs(dialog, lw, stack, tabs, iface)
    frame.layout().insertWidget(0, widget)
    if list_frame is not None:
        changes.set(list_frame, "visible", False)
    changes.add(widget.remove)


class SymbologyTree(QWidget):
    """ArcMap's "Show:" tree beside the QGIS renderer page."""

    def __init__(self, renderer_dialog, combo, parent_dialog):
        super().__init__(renderer_dialog)
        from qgis.PyQt.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout

        self.setObjectName("ArcMapSymbologyTree")
        self.combo = combo
        self.parent_dialog = parent_dialog
        self._syncing = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.addWidget(QLabel(tr("Show:"), self))
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setFixedWidth(170)
        self.items = {}
        for group, entries in SYMBOLOGY_TREE:
            top = QTreeWidgetItem(self.tree, [tr(group)])
            top.setFlags(Qt.ItemFlag.ItemIsEnabled)
            for text, target in entries:
                if isinstance(target, str) and combo.findData(target) < 0:
                    continue
                item = QTreeWidgetItem(top, [tr(text)])
                item.setData(0, Qt.ItemDataRole.UserRole, target)
                self.items.setdefault(target, item)
            top.setExpanded(True)
        layout.addWidget(self.tree, 1)
        self.tree.currentItemChanged.connect(self._picked)
        combo.currentIndexChanged.connect(self._combo_changed)
        self._combo_changed(combo.currentIndex())

    def _picked(self, current, previous):
        if self._syncing or current is None:
            return
        target = current.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(target, tuple) and target[0] == "page":
            self._open_page(target[1])
        elif isinstance(target, str):
            index = self.combo.findData(target)
            if index >= 0:
                self._syncing = True
                self.combo.setCurrentIndex(index)
                self._syncing = False

    def _combo_changed(self, index):
        if self._syncing:
            return
        target = self.combo.itemData(index)
        item = self.items.get(target)
        if item is not None:
            self._syncing = True
            self.tree.setCurrentItem(item)
            self._syncing = False

    def _open_page(self, title):
        from qgis.PyQt.QtWidgets import QListWidget

        lw = self.parent_dialog.findChild(QListWidget, "mOptionsListWidget") if self.parent_dialog else None
        if lw is None:
            return
        for i in range(lw.count()):
            item = lw.item(i)
            if (item.data(Qt.ItemDataRole.UserRole + 42) or item.text()) == title:
                lw.setCurrentRow(i)
                return


def dress_symbol_selector(dialog):
    """ArcMap's Symbol Selector wording: full gallery, Properties button."""
    from qgis.PyQt.QtWidgets import QComboBox, QPushButton

    if dialog.property(PAGES_DONE):
        return
    dialog.setProperty(PAGES_DONE, True)
    dialog.setWindowTitle(tr("Symbol Selector"))
    combo = dialog.findChild(QComboBox, "groupsCombo")
    if combo is not None:
        index = combo.findText("All Symbols")
        if index >= 0:
            combo.setCurrentIndex(index)
    for name, caption in (("btnAdvanced", "Properties"), ("btnSaveSymbol", "Save As…"),
                          ("openStyleManagerButton", "Style References…")):
        for b in dialog.findChildren(QPushButton, name):
            b.setText(tr(caption))


def dress_renderer_combos(widget):
    """ArcMap renderer wording, the "Show:" tree and ArcMap button captions."""
    from qgis.PyQt.QtWidgets import QComboBox, QGridLayout, QHBoxLayout, QPushButton, QVBoxLayout

    for combo in widget.findChildren(QComboBox, "cboRenderers"):
        if combo.property(PAGES_DONE):
            continue
        combo.setProperty(PAGES_DONE, True)
        for i in range(combo.count()):
            new = RENDERERS.get(combo.itemData(i))
            if new:
                combo.setItemText(i, tr(new))
        # the renderer properties widget that owns the combo
        owner = combo.parentWidget()
        while owner is not None and owner.metaObject().className() != "QgsRendererPropertiesDialog":
            owner = owner.parentWidget()
        if owner is None or owner.layout() is None or owner.property("arcmapTree"):
            continue
        owner.setProperty("arcmapTree", True)
        try:
            old = owner.layout()
            container = QWidget(owner)
            inner = QVBoxLayout(container)
            inner.setContentsMargins(0, 0, 0, 0)
            items = []
            while old.count():
                items.append(old.takeAt(0))
            for item in items:
                if item.widget() is not None:
                    inner.addWidget(item.widget())
                elif item.layout() is not None:
                    inner.addLayout(item.layout())
                elif item.spacerItem() is not None:
                    inner.addItem(item)
            row = QHBoxLayout()
            tree = SymbologyTree(owner, combo, widget)
            row.addWidget(tree)
            row.addWidget(container, 1)
            if isinstance(old, QGridLayout):
                old.addLayout(row, 0, 0)
            else:
                old.addLayout(row)
        except Exception:  # noqa: BLE001
            import traceback

            traceback.print_exc()
    for name, caption in SYMBOLOGY_BUTTONS.items():
        for button in widget.findChildren(QPushButton, name):
            if not button.property(PAGES_DONE):
                button.setProperty(PAGES_DONE, True)
                button.setText(tr(caption))


class WindowDresser(QObject):
    """Dress attribute tables as they gain focus."""

    def __init__(self, iface, changes):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.changes = changes
        app = QGuiApplication.instance()
        app.focusWindowChanged.connect(self.dress)
        for w in QApplication.topLevelWidgets():
            if w.isVisible():
                self.dress_window(w)

    def dress(self, window):
        if window is None:
            return
        for w in QApplication.topLevelWidgets():
            if w.windowHandle() is window:
                self.dress_window(w)
                break

    def dress_window(self, widget):
        candidates = [widget] + widget.findChildren(QDialog)
        for w in candidates:
            if w.metaObject().className() in TABS_BY_CLASS:
                dress_layer_properties(self.changes, w, self.iface)
            if w.metaObject().className() == "QgsSymbolSelectorDialog":
                dress_symbol_selector(w)
            dress_renderer_combos(w)
            if w.objectName().startswith("QgsAttributeTableDialog") and not w.property(TABLE_DONE):
                try:
                    dress_attribute_table(self.changes, w, self.iface)
                except Exception:  # noqa: BLE001
                    import traceback

                    traceback.print_exc()
                    w.setProperty(TABLE_DONE, True)

    def stop(self):
        app = QGuiApplication.instance()
        if app is not None:
            try:
                app.focusWindowChanged.disconnect(self.dress)
            except (TypeError, RuntimeError):
                pass
        for w in QApplication.topLevelWidgets():
            for d in [w] + w.findChildren(QDialog):
                if d.property(TABLE_DONE):
                    d.setProperty(TABLE_DONE, None)


def dress_windows(iface, changes):
    from .attribute_table import dock_tables

    dock_tables(changes)
    dresser = WindowDresser(iface, changes)
    changes.add(dresser.stop)
    return dresser
