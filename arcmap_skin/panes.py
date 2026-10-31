# -*- coding: utf-8 -*-
"""Dock panes arranged and titled like ArcMap.

* Layers → **Table Of Contents** (left) with the List By buttons
  (:mod:`contents_views`).
* Browser → **Catalog** (right), Processing Toolbox → **ArcToolbox** (right,
  tabbed with Catalog), Layer Styling → **Symbology** (right, tabbed).
* :class:`ActivePane` marks the focused dock with the ``arcmapActive``
  property so the stylesheet can colour its title bar.

Dock positions come back with the saved window state; titles and other
changes are reverted through :class:`util.Changes`.
"""

from qgis.PyQt.QtCore import QEvent, QObject, Qt, QTimer
from qgis.PyQt.QtWidgets import QApplication, QDockWidget, QLineEdit, QToolBar, QWidget

from . import contents_views, toolbars
from .util import alive, arcmap_icon, find_dock, tr

LEFT = Qt.DockWidgetArea.LeftDockWidgetArea
RIGHT = Qt.DockWidgetArea.RightDockWidgetArea
BOTTOM = Qt.DockWidgetArea.BottomDockWidgetArea

# objectName → (ArcMap title, default area, tabify with)
PANES = {
    "Layers": ("Table Of Contents", LEFT, None),
    "Browser": ("Catalog", RIGHT, None),
    "ArcMapToolboxDock": ("ArcToolbox", RIGHT, "Browser"),
    "ProcessingToolbox": ("Search", RIGHT, "Browser"),
    "ArcMapCreateFeaturesDock": ("Create Features", RIGHT, "Browser"),
    "IdentifyResultsDock": ("Identify", RIGHT, "Browser"),
    "ResultsViewer": ("Results", RIGHT, "Browser"),
    "LayerStyling": ("Symbology", RIGHT, "Browser"),
    "Overview": ("Overview", LEFT, "Layers"),
    "MessageLog": ("Log Messages", BOTTOM, None),
    "undo/redo dock": ("Undo/Redo", RIGHT, "Browser"),
    "BookmarksDockWidget": ("Bookmarks", RIGHT, "Browser"),
    "StatisticalSummaryDockWidget": ("Statistics", RIGHT, "Browser"),
    "AdvancedDigitizingTools": ("Create Features", RIGHT, "Browser"),
    "VertexEditor": ("Sketch Properties", RIGHT, "Browser"),
    "LayerOrder": ("Drawing Order", LEFT, "Layers"),
    "ProcessingResults": ("Results", RIGHT, "Browser"),
}

DEFAULT_OPEN = ["Layers", "Browser", "ArcMapToolboxDock"]


class TitleKeeper(QObject):
    """Keep our dock title even when QGIS resets it (e.g. on project load)."""

    def __init__(self, dock, title):
        super().__init__(dock)
        self.dock = dock
        self.title = title
        self._armed = False
        dock.installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802
        if event.type() == QEvent.Type.WindowTitleChange and not self._armed:
            if obj.windowTitle() != self.title:
                self._armed = True
                QTimer.singleShot(0, self._fix)
        return False

    def _fix(self):
        self._armed = False
        if alive(self.dock) and self.dock.windowTitle() != self.title:
            self.dock.setWindowTitle(self.title)

    def stop(self):
        if alive(self.dock):
            self.dock.removeEventFilter(self)


class ActivePane(QObject):
    """Set ``arcmapActive`` on the dock that holds keyboard focus."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.current = None
        QApplication.instance().focusChanged.connect(self.focus_changed)

    def focus_changed(self, old, new):
        dock = None
        w = new
        while w is not None:
            if isinstance(w, QDockWidget):
                dock = w
                break
            w = w.parentWidget()
        if dock is not None and dock.parent() is not self.win:
            dock = None
        self._set(dock)

    def _set(self, dock):
        if dock is self.current:
            return
        if alive(self.current):
            self._mark(self.current, False)
        self.current = dock
        if alive(dock):
            self._mark(dock, True)

    @staticmethod
    def _mark(dock, on):
        dock.setProperty("arcmapActive", "true" if on else "false")
        style = dock.style()
        style.unpolish(dock)
        style.polish(dock)
        dock.update()

    def stop(self):
        try:
            QApplication.instance().focusChanged.disconnect(self.focus_changed)
        except (TypeError, RuntimeError):
            pass
        if alive(self.current):
            self._mark(self.current, False)
        self.current = None


def _retitle(changes, dock, title):
    title = tr(title)
    changes.set(dock, "windowTitle", title)
    keeper = TitleKeeper(dock, title)
    changes.add(keeper.stop)


IDENTIFY_MODES = [
    ("<Top-most layer>", 1),
    ("<Visible layers>", 2),
    ("<Selectable layers>", 2),
    ("<Current layer>", 0),
    ("<Choose layers…>", 3),
]


def _dress_identify(changes, dock):
    """ArcMap's "Identify from:" selector above the Identify results."""
    from qgis.core import QgsSettings
    from qgis.PyQt.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout

    old = dock.widget()
    if old is None or dock.property("arcmapIdentify"):
        return
    dock.setProperty("arcmapIdentify", True)
    container = QWidget(dock)
    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    row = QHBoxLayout()
    row.setContentsMargins(4, 2, 4, 0)
    row.addWidget(QLabel(tr("Identify from:"), container))
    combo = QComboBox(container)
    combo.setObjectName("ArcMapIdentifyFrom")
    for text, mode in IDENTIFY_MODES:
        combo.addItem(tr(text), mode)
    current = QgsSettings().value("Map/identifyMode", 1, type=int)
    index = next((i for i in range(combo.count()) if combo.itemData(i) == current), 0)
    combo.setCurrentIndex(index)
    combo.currentIndexChanged.connect(lambda i: QgsSettings().setValue("Map/identifyMode", combo.itemData(i)))
    row.addWidget(combo, 1)
    layout.addLayout(row)
    layout.addWidget(old, 1)
    dock.setWidget(container)

    def undo(dock=dock, old=old, container=container):
        if alive(dock) and alive(old):
            old.setParent(dock)
            dock.setWidget(old)
            dock.setProperty("arcmapIdentify", None)
        if alive(container):
            container.deleteLater()

    changes.add(undo)


def _dress_catalog(changes, dock, actions):
    dock.setWindowIcon(arcmap_icon("catalog"))
    # ArcCatalog shows a preview/properties panel under the tree
    from qgis.PyQt.QtGui import QAction

    for action in dock.findChildren(QAction):
        text = (action.text() + action.objectName()).lower()
        if "propert" in text and action.isCheckable():
            action.setToolTip(tr("Preview / properties of the selected item"))
            break
    connect = actions.get("connect_folder") if actions else None
    if connect is None:
        return
    for tb in dock.findChildren(QToolBar):
        first = tb.actions()[0] if tb.actions() else None
        if first is not None:
            tb.insertAction(first, connect)
        else:
            tb.addAction(connect)

        def undo(tb=tb, connect=connect):
            if alive(tb):
                tb.removeAction(connect)

        changes.add(undo)
        break


class DockWatcher(QObject):
    """Retitle docks QGIS creates later (Identify Results, Results Viewer)."""

    def __init__(self, win, changes):
        super().__init__(win)
        self.win = win
        self.changes = changes
        win.installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802
        if event.type() == QEvent.Type.ChildAdded:
            QTimer.singleShot(0, self._check)
        return False

    def _check(self):
        if not alive(self.win):
            return
        for dock in self.win.findChildren(QDockWidget):
            name = dock.objectName()
            if dock.parent() is self.win and name in PANES and not dock.property("arcmapTitled"):
                dock.setProperty("arcmapTitled", True)
                _retitle(self.changes, dock, PANES[name][0])
                if name == "IdentifyResultsDock":
                    _dress_identify(self.changes, dock)

    def stop(self):
        if alive(self.win):
            self.win.removeEventFilter(self)


def _dress_toolbox(changes, dock):
    search = dock.findChild(QLineEdit, "searchBox")
    if search is not None:
        changes.set(search, "placeholderText", tr("Search For Tools"))


def arrange_panes(iface, changes, actions=None):
    win = iface.mainWindow()
    for name, (title, _area, _tab) in PANES.items():
        dock = find_dock(win, name)
        if dock is None:
            continue
        _retitle(changes, dock, title)
        dock.setProperty("arcmapTitled", True)
        if name == "Browser":
            _dress_catalog(changes, dock, actions)
        elif name == "IdentifyResultsDock":
            _dress_identify(changes, dock)
        elif name == "ProcessingToolbox":
            _dress_toolbox(changes, dock)
    layers = find_dock(win, "Layers")
    if layers is not None:
        contents_views.dress_contents(iface, changes, layers, actions or {})
    tracker = ActivePane(win)
    changes.add(tracker.stop)
    watcher = DockWatcher(win, changes)
    changes.add(watcher.stop)

    def untitle():
        for dock in win.findChildren(QDockWidget):
            if dock.property("arcmapTitled"):
                dock.setProperty("arcmapTitled", None)

    changes.add(untitle)


def reset_panes(win, close_others=False):
    """Dock the panes in ArcMap's default arrangement."""
    first_in_area = {}
    for name, (title, area, tab_with) in PANES.items():
        dock = find_dock(win, name)
        if dock is None:
            continue
        dock.setFloating(False)
        if tab_with is not None:
            partner = find_dock(win, tab_with)
            if partner is not None:
                win.addDockWidget(area, dock)
                win.tabifyDockWidget(partner, dock)
                continue
        win.addDockWidget(area, dock)
        first_in_area.setdefault(area, dock)
    for name in PANES:
        dock = find_dock(win, name)
        if dock is None:
            continue
        dock.setVisible(name in DEFAULT_OPEN)
    if close_others:
        for dock in win.findChildren(QDockWidget):
            if dock.parent() is win and dock.objectName() not in PANES:
                dock.setVisible(False)
    for name in ("Layers", "Browser"):
        dock = find_dock(win, name)
        if dock is not None:
            dock.raise_()
    # Give the TOC a sensible width.
    layers = find_dock(win, "Layers")
    if layers is not None:
        try:
            win.resizeDocks([layers], [280], Qt.Orientation.Horizontal)
        except Exception:  # noqa: BLE001  (older Qt)
            pass


def ensure_native_toolbars_hidden(win):
    toolbars.hide_replaced_native(win)
