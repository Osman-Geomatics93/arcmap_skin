# -*- coding: utf-8 -*-
"""The attribute table dressed as ArcMap's Table window.

Applied to every ``QgsAttributeTableDialog`` as it appears (see
:class:`dialogs.WindowDresser`):

* Toolbar in ArcMap's order behind a *Table Options ▾* menu (Find and
  Replace, Select By Attributes, Clear/Switch/Select All, Add Field, Turn
  All Fields On, Restore Default Column Widths, Arrange Fields, Joins and
  Relates, Export, Field Calculator, Appearance, Reload Cache …).
* Field-header right-click menu: Sort Ascending/Descending, Summarize,
  Statistics, Field Calculator, Calculate Geometry, Turn Field Off, Turn
  All Fields On, Autosize, Delete Field, Properties.
* Row right-click menu: Flash, Zoom To, Pan To, Identify, Select/Unselect,
  Copy Selected, Delete Selected.
* Record navigator footer with Show All / Show Selected and
  "(n out of m Selected)".
* Tables dock into one tabbed *Table* window, tabs named after the layer.

Everything is recorded in ``Changes`` and undone when the look goes off.
QGIS's own widget-based actions (feature actions, dock/undock) are left in
place: removing them from the toolbar would delete them.
"""

from qgis.core import QgsFeatureRequest, QgsProject, QgsSettings
from qgis.gui import QgsAttributeTableFilterModel, QgsDualView
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QEvent, QObject, Qt, QTimer
from qgis.PyQt.QtGui import QAction, QIntValidator
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDockWidget,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from .util import alive, arcmap_icon, has_icon, separator, tool_button, tr

TABLE_DONE = "arcmapTableDone"
SEP = None

# ArcMap toolbar: (QGIS action objectName or "@custom", icon, caption)
TOOLBAR = [
    ("mActionToggleEditing", "editor", "Start/Stop Editing"),
    ("mActionSaveEdits", "save_edits", "Save Edits"),
    SEP,
    ("@related", "spatial_join", "Related Tables"),
    ("@select_by_attributes", "select_by_attributes", "Select By Attributes"),
    ("mActionInvertSelection", "switch_selection", "Switch Selection"),
    ("mActionRemoveSelection", "clear_selected", "Clear Selection"),
    ("mActionZoomMapToSelectedRows", "zoom_selected", "Zoom To Selected"),
    ("mActionPanMapToSelectedRows", "pan_selected", "Pan To Selected"),
    ("mActionDeleteSelected", "delete", "Delete Selected"),
    SEP,
    ("mActionAddFeature", "add_record", "Add Record"),
    ("mActionOpenFieldCalculator", "field_calculator", "Field Calculator"),
]

# Table Options ▾ in ArcMap's order: (QGIS action objectName or "@custom", icon, caption)
TABLE_OPTIONS = [
    ("@find_replace", "find", "Find and Replace…"),
    ("@select_by_attributes", "select_by_attributes", "Select By Attributes…"),
    ("mActionRemoveSelection", "clear_selected", "Clear Selection"),
    ("mActionInvertSelection", "switch_selection", "Switch Selection"),
    ("mActionSelectAll", "select_all", "Select All"),
    SEP,
    ("mActionAddAttribute", "add_field", "Add Field…"),
    ("@turn_all_on", None, "Turn All Fields On"),
    ("@restore_widths", None, "Restore Default Column Widths"),
    ("mActionOrganizeColumns", None, "Arrange Fields…"),
    SEP,
    ("@joins", "spatial_join", "Joins and Relates"),
    ("@related", None, "Related Tables"),
    SEP,
    ("mActionSelectedToTop", "selected_to_top", "Move Selected To Top"),
    ("mActionSearchForm", None, "Select By Form…"),
    ("mActionOpenFieldCalculator", "field_calculator", "Field Calculator…"),
    ("mActionSetStyles", None, "Appearance (Conditional Formatting)…"),
    SEP,
    ("@reload", "refresh", "Reload Cache"),
    ("@export", "export_map", "Export…"),
    ("@properties", "properties", "Layer Properties…"),
]

# QGIS actions kept out of the ArcMap menus (they stay reachable under "QGIS")
_LEFTOVER_SKIP = set()


def _layer_of(dialog):
    name = dialog.objectName()
    if "/" not in name:
        return None
    return QgsProject.instance().mapLayer(name.split("/", 1)[1])


def _dual_view(dialog):
    dual = dialog.findChild(QgsDualView) or dialog.findChild(QWidget, "mMainView")
    if dual is None:
        dual = next((w for w in dialog.findChildren(QWidget) if w.metaObject().className() == "QgsDualView"), None)
    if dual is not None and not isinstance(dual, QgsDualView):
        try:
            dual = sip.cast(dual, QgsDualView)
        except (TypeError, ValueError):
            dual = None
    return dual


# ---------------------------------------------------------------- footer


class TableFooter(QWidget):
    """ArcMap record navigator: |◀ ◀ [n] ▶ ▶|  Show: All Selected  (x out of y Selected)."""

    def __init__(self, dialog, layer, dual):
        super().__init__(dialog)
        self.setObjectName("ArcMapTableFooter")
        self.layer = layer
        self.dual = dual
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        self.first = tool_button(arcmap_icon("first_record"), tr("First record"), parent=self)
        self.prev = tool_button(arcmap_icon("prev_record"), tr("Previous record"), parent=self)
        self.index = QLineEdit("0", self)
        self.index.setObjectName("ArcMapRecordIndex")
        self.index.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.index.setValidator(QIntValidator(0, 2_000_000_000, self))
        self.index.setFixedWidth(56)
        self.next = tool_button(arcmap_icon("next_record"), tr("Next record"), parent=self)
        self.last = tool_button(arcmap_icon("last_record"), tr("Last record"), parent=self)
        for w in (self.first, self.prev, self.index, self.next, self.last):
            layout.addWidget(w)
        layout.addWidget(separator(self))
        layout.addWidget(QLabel(tr("Show:"), self))
        self.show_all = tool_button(arcmap_icon("show_all_records"), tr("Show all records"), checkable=True, parent=self)
        self.show_all.setText(tr("All"))
        self.show_selected = tool_button(
            arcmap_icon("show_selected_records"), tr("Show selected records"), checkable=True, parent=self
        )
        self.show_selected.setText(tr("Selected"))
        for b in (self.show_all, self.show_selected):
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setAutoExclusive(True)
            layout.addWidget(b)
        self.show_all.setChecked(True)
        layout.addWidget(separator(self))
        self.label = QLabel("", self)
        self.label.setObjectName("ArcMapRecordCount")
        layout.addWidget(self.label)
        layout.addStretch(1)

        self.first.clicked.connect(lambda: self.go(0))
        self.prev.clicked.connect(lambda: self.go(self.current() - 1))
        self.next.clicked.connect(lambda: self.go(self.current() + 1))
        self.last.clicked.connect(lambda: self.go(self.count() - 1))
        self.index.returnPressed.connect(self._typed)
        self.show_all.clicked.connect(lambda: self._filter(QgsAttributeTableFilterModel.FilterMode.ShowAll))
        self.show_selected.clicked.connect(lambda: self._filter(QgsAttributeTableFilterModel.FilterMode.ShowSelected))

        layer.selectionChanged.connect(self.update_label)
        layer.featureAdded.connect(self.update_label)
        layer.featureDeleted.connect(self.update_label)
        view = self._view()
        if view is not None and view.selectionModel() is not None:
            view.selectionModel().currentRowChanged.connect(self._current_changed)
        self.update_label()

    def _view(self):
        return self.dual.tableView() if alive(self.dual) else None

    def count(self):
        view = self._view()
        return view.model().rowCount() if view is not None and view.model() is not None else 0

    def current(self):
        view = self._view()
        if view is None or not view.currentIndex().isValid():
            return -1
        return view.currentIndex().row()

    def go(self, row):
        view = self._view()
        if view is None or view.model() is None:
            return
        row = max(0, min(row, self.count() - 1))
        if row < 0:
            return
        index = view.model().index(row, 0)
        view.setCurrentIndex(index)
        view.scrollTo(index)
        self.index.setText(str(row + 1))

    def _typed(self):
        try:
            self.go(int(self.index.text()) - 1)
        except ValueError:
            pass

    def _current_changed(self, current, previous):
        if current.isValid():
            self.index.setText(str(current.row() + 1))

    def _filter(self, mode):
        if alive(self.dual):
            self.dual.setFilterMode(mode)
            QTimer.singleShot(0, self.update_label)

    def update_label(self, *_):
        if not alive(self.layer):
            return
        shown = self.count()
        total = self.layer.featureCount()
        selected = self.layer.selectedFeatureCount()
        if shown != total and shown >= 0:
            text = tr("(%d out of %d Selected, %d shown)") % (selected, total, shown)
        else:
            text = tr("(%d out of %d Selected)") % (selected, total)
        self.label.setText(text)

    def remove(self):
        if alive(self.layer):
            for signal in (self.layer.selectionChanged, self.layer.featureAdded, self.layer.featureDeleted):
                try:
                    signal.disconnect(self.update_label)
                except (TypeError, RuntimeError):
                    pass
        self.hide()
        self.setParent(None)
        self.deleteLater()


# ------------------------------------------------------- find and replace


class FindReplaceDialog(QDialog):
    def __init__(self, dialog, layer, dual, iface):
        super().__init__(dialog)
        self.setWindowTitle(tr("Find and Replace"))
        self.layer = layer
        self.dual = dual
        self.iface = iface
        self._last_row = -1
        form = QFormLayout(self)
        self.find_text = QLineEdit(self)
        form.addRow(tr("Find what:"), self.find_text)
        self.replace_text = QLineEdit(self)
        form.addRow(tr("Replace with:"), self.replace_text)
        self.field = QComboBox(self)
        self.field.addItem(tr("<All fields>"), "")
        for f in layer.fields():
            self.field.addItem(f.name(), f.name())
        form.addRow(tr("Search in:"), self.field)
        self.match_case = QCheckBox(tr("Match case"), self)
        self.whole = QCheckBox(tr("Match whole field"), self)
        form.addRow(self.match_case)
        form.addRow(self.whole)
        row = QHBoxLayout()
        for text, slot in ((tr("Find Next"), self.find_next), (tr("Replace"), self.replace),
                           (tr("Replace All"), self.replace_all), (tr("Close"), self.close)):
            b = QPushButton(text, self)
            b.clicked.connect(slot)
            row.addWidget(b)
        form.addRow(row)
        self.status = QLabel("", self)
        form.addRow(self.status)

    def _matches(self, value):
        if value is None:
            return False
        s = str(value)
        needle = self.find_text.text()
        if not self.match_case.isChecked():
            s, needle = s.lower(), needle.lower()
        return s == needle if self.whole.isChecked() else needle in s

    def _fields(self):
        name = self.field.currentData()
        return [name] if name else [f.name() for f in self.layer.fields()]

    def find_next(self):
        view = self.dual.tableView() if alive(self.dual) else None
        model = view.model() if view is not None else None
        if model is None or not self.find_text.text():
            return False
        rows = model.rowCount()
        fields = self._fields()
        start = self._last_row + 1
        for offset in range(rows):
            row = (start + offset) % rows
            fid = model.rowToId(model.index(row, 0))
            feat = self.layer.getFeature(fid)
            if any(self._matches(feat[name]) for name in fields):
                self._last_row = row
                self.layer.selectByIds([fid])
                index = model.index(row, 0)
                view.setCurrentIndex(index)
                view.scrollTo(index)
                self.status.setText(tr("Found in row %d") % (row + 1))
                return True
        self.status.setText(tr("No more matches"))
        self._last_row = -1
        return False

    def _replace_in(self, feat, fields):
        changed = False
        needle = self.find_text.text()
        for name in fields:
            value = feat[name]
            if not self._matches(value):
                continue
            idx = self.layer.fields().indexOf(name)
            if self.whole.isChecked():
                new = self.replace_text.text()
            elif self.match_case.isChecked():
                new = str(value).replace(needle, self.replace_text.text())
            else:
                import re

                new = re.sub(re.escape(needle), lambda m: self.replace_text.text(), str(value), flags=re.IGNORECASE)
            if self.layer.changeAttributeValue(feat.id(), idx, new):
                changed = True
        return changed

    def _editable(self):
        if not self.layer.isEditable():
            QMessageBox.information(self, self.windowTitle(), tr("Start editing to replace values."))
            return False
        return True

    def replace(self):
        if not self._editable():
            return
        if self._last_row < 0 and not self.find_next():
            return
        view = self.dual.tableView()
        model = view.model()
        fid = model.rowToId(model.index(self._last_row, 0))
        self._replace_in(self.layer.getFeature(fid), self._fields())
        self.find_next()

    def replace_all(self):
        if not self._editable():
            return
        fields = self._fields()
        count = 0
        self.layer.beginEditCommand(tr("Replace All"))
        for feat in self.layer.getFeatures(QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry)):
            if self._replace_in(feat, fields):
                count += 1
        self.layer.endEditCommand()
        self.status.setText(tr("%d record(s) changed") % count)


# ------------------------------------------------------------- context menus


class TableMenus(QObject):
    """ArcMap field-header and row context menus on the table view."""

    def __init__(self, dialog, layer, dual, iface, qgis_actions):
        super().__init__(dialog)
        self.dialog = dialog
        self.layer = layer
        self.dual = dual
        self.iface = iface
        self.qgis = qgis_actions
        view = dual.tableView()
        self.view = view
        self.header = view.horizontalHeader()
        self.header.installEventFilter(self)
        view.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802
        if event.type() == QEvent.Type.ContextMenu:
            if obj is self.header:
                self.header_menu(event.pos(), event.globalPos())
                return True
            if obj is self.view.viewport():
                self.row_menu(event.pos(), event.globalPos())
                return True
        return False

    # ---- helpers

    def _model(self):
        return self.view.model()

    def _field_index(self, column):
        model = self._model()
        try:
            source = model.mapToSource(model.index(0, column)) if model.rowCount() else None
            src_col = source.column() if source is not None and source.isValid() else column
            return model.sourceModel().fieldIdx(src_col)
        except Exception:  # noqa: BLE001
            name = model.headerData(column, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
            return self.layer.fields().lookupField(str(name))

    def _field_name(self, column):
        idx = self._field_index(column)
        return self.layer.fields()[idx].name() if idx is not None and idx >= 0 else None

    def _trigger(self, name):
        action = self.qgis.get(name)
        if action is not None:
            action.trigger()

    def _run(self, alg, params):
        try:
            from processing import execAlgorithmDialog

            execAlgorithmDialog(alg, params)
        except ImportError:
            pass

    # ---- header

    def header_menu(self, pos, global_pos):
        column = self.header.logicalIndexAt(pos)
        name = self._field_name(column) if column >= 0 else None
        menu = QMenu(self.view)
        menu.setObjectName("ArcMapFieldMenu")
        if name:
            menu.addAction(arcmap_icon("sort_asc"), tr("Sort Ascending"),
                           lambda: self.view.sortByColumn(column, Qt.SortOrder.AscendingOrder))
            menu.addAction(arcmap_icon("sort_desc"), tr("Sort Descending"),
                           lambda: self.view.sortByColumn(column, Qt.SortOrder.DescendingOrder))
            menu.addSeparator()
            menu.addAction(arcmap_icon("statistics"), tr("Summarize…"),
                           lambda: self._run("qgis:statisticsbycategories",
                                             {"INPUT": self.layer, "CATEGORIES_FIELD_NAME": [name]}))
            menu.addAction(arcmap_icon("statistics"), tr("Statistics…"),
                           lambda: self._run("qgis:basicstatisticsforfields", {"INPUT_LAYER": self.layer, "FIELD_NAME": name}))
            menu.addAction(arcmap_icon("field_calculator"), tr("Field Calculator…"),
                           lambda: self._trigger("mActionOpenFieldCalculator"))
            menu.addAction(arcmap_icon("field_calculator"), tr("Calculate Geometry…"),
                           lambda: self._run("qgis:exportaddgeometrycolumns", {"INPUT": self.layer}))
            menu.addSeparator()
            menu.addAction(arcmap_icon("field_off"), tr("Turn Field Off"), lambda: self.hide_field(name))
        menu.addAction(tr("Turn All Fields On"), self.show_all_fields)
        if column >= 0:
            menu.addAction(tr("Autosize Column"), lambda: self.view.resizeColumnToContents(column))
        menu.addAction(tr("Restore Default Column Widths"), self.view.resizeColumnsToContents)
        menu.addSeparator()
        if name:
            menu.addAction(arcmap_icon("delete"), tr("Delete Field…"), lambda: self._trigger("mActionRemoveAttribute"))
        menu.addAction(arcmap_icon("properties"), tr("Properties…"),
                       lambda: self.iface.showLayerProperties(self.layer, "Fields"))
        menu.exec(global_pos)

    def hide_field(self, name):
        config = self.layer.attributeTableConfig()
        columns = config.columns()
        for col in columns:
            if col.name == name:
                col.hidden = True
        config.setColumns(columns)
        self.layer.setAttributeTableConfig(config)

    def show_all_fields(self):
        config = self.layer.attributeTableConfig()
        columns = config.columns()
        for col in columns:
            col.hidden = False
        config.setColumns(columns)
        self.layer.setAttributeTableConfig(config)

    # ---- rows

    def row_menu(self, pos, global_pos):
        index = self.view.indexAt(pos)
        model = self._model()
        fid = model.rowToId(index) if index.isValid() else None
        canvas = self.iface.mapCanvas()
        layer = self.layer
        menu = QMenu(self.view)
        menu.setObjectName("ArcMapRowMenu")
        if fid is not None:
            menu.addAction(arcmap_icon("identify"), tr("Flash"), lambda: canvas.flashFeatureIds(layer, [fid]))
            menu.addAction(arcmap_icon("zoom_selected"), tr("Zoom To"), lambda: canvas.zoomToFeatureIds(layer, [fid]))
            menu.addAction(arcmap_icon("pan_selected"), tr("Pan To"), lambda: canvas.panToFeatureIds(layer, [fid]))
            menu.addAction(arcmap_icon("identify"), tr("Identify…"),
                           lambda: self.iface.openFeatureForm(layer, layer.getFeature(fid)))
            menu.addSeparator()
            if fid in layer.selectedFeatureIds():
                menu.addAction(tr("Unselect"), lambda: layer.deselect(fid))
            else:
                menu.addAction(arcmap_icon("select_rect"), tr("Select"), lambda: layer.select(fid))
        menu.addAction(arcmap_icon("select_all"), tr("Select All"), lambda: self._trigger("mActionSelectAll"))
        menu.addAction(arcmap_icon("clear_selected"), tr("Clear Selected"), lambda: self._trigger("mActionRemoveSelection"))
        menu.addSeparator()
        menu.addAction(arcmap_icon("copy"), tr("Copy Selected"), lambda: self._trigger("mActionCopySelectedRows"))
        menu.addAction(arcmap_icon("delete"), tr("Delete Selected"), lambda: self._trigger("mActionDeleteSelected"))
        menu.exec(global_pos)

    def stop(self):
        if alive(self.header):
            self.header.removeEventFilter(self)
        if alive(self.view) and alive(self.view.viewport()):
            self.view.viewport().removeEventFilter(self)


# ------------------------------------------------------------------ dress


def dress_attribute_table(changes, dialog, iface=None):
    """Rebuild the table as ArcMap's Table window. Safe to call once per dialog."""
    if iface is None:
        from qgis.utils import iface as _iface

        iface = _iface
    toolbar = dialog.findChild(QToolBar, "mToolbar")
    layer = _layer_of(dialog)
    dual = _dual_view(dialog)
    if toolbar is None or layer is None or dual is None:
        return
    dialog.setProperty(TABLE_DONE, True)
    originals = list(toolbar.actions())
    by_name = {a.objectName(): a for a in originals if a.objectName()}

    # --- custom commands
    custom = {}

    def make(key, text, icon, callback):
        a = QAction(arcmap_icon(icon) if icon else None, tr(text), dialog) if icon else QAction(tr(text), dialog)
        a.setObjectName("ArcMapTable_" + key)
        a.triggered.connect(callback)
        custom[key] = a
        return a

    def select_by_attributes():
        from .query_builder import open_select_by_attributes

        open_select_by_attributes(iface, layer)

    def find_replace():
        dlg = FindReplaceDialog(dialog, layer, dual, iface)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dlg.show()

    def related():
        iface.showLayerProperties(layer, "Relations")

    def reload():
        if layer.dataProvider() is not None:
            layer.dataProvider().reloadData()
        layer.triggerRepaint()

    def export():
        a = iface.mainWindow().findChild(QAction, "mActionLayerSaveAs")
        iface.setActiveLayer(layer)
        if a is not None:
            a.trigger()

    menus_holder = {}

    def turn_all_on():
        if "menus" in menus_holder:
            menus_holder["menus"].show_all_fields()

    def restore_widths():
        dual.tableView().resizeColumnsToContents()

    make("select_by_attributes", "Select By Attributes…", "select_by_attributes", select_by_attributes)
    make("find_replace", "Find and Replace…", "find", find_replace)
    make("related", "Related Tables", "spatial_join", related)
    make("reload", "Reload Cache", "refresh", reload)
    make("export", "Export…", "export_map", export)
    make("turn_all_on", "Turn All Fields On", None, turn_all_on)
    make("restore_widths", "Restore Default Column Widths", None, restore_widths)
    make("properties", "Layer Properties…", "properties", lambda: iface.showLayerProperties(layer))

    def resolve(name):
        if name.startswith("@"):
            return custom.get(name[1:])
        return by_name.get(name)

    # --- rebuild the toolbar (widget actions stay in place)
    widget_actions = [a for a in originals if isinstance(a, QWidgetAction)]
    for a in originals:
        if not isinstance(a, QWidgetAction):
            toolbar.removeAction(a)
    anchor = widget_actions[0] if widget_actions else None

    def add(thing):
        if isinstance(thing, QAction):
            toolbar.insertAction(anchor, thing) if anchor is not None else toolbar.addAction(thing)
        else:
            toolbar.insertWidget(anchor, thing) if anchor is not None else toolbar.addWidget(thing)

    def add_separator():
        toolbar.insertSeparator(anchor) if anchor is not None else toolbar.addSeparator()

    changes.set(toolbar, "toolButtonStyle", Qt.ToolButtonStyle.ToolButtonIconOnly)

    options = QMenu(toolbar)
    options.setObjectName("ArcMapTableOptionsMenu")
    used = set()
    pending = False
    for entry in TABLE_OPTIONS:
        if entry is None:
            pending = bool(options.actions())
            continue
        name, icon, caption = entry
        action = resolve(name)
        if action is None or isinstance(action, QWidgetAction):
            continue
        if pending:
            options.addSeparator()
            pending = False
        if name == "@joins":
            joins = options.addMenu(arcmap_icon("spatial_join"), tr("Joins and Relates"))
            joins.addAction(tr("Join…"), lambda: _run_alg("native:joinattributestable", {"INPUT": layer}))
            joins.addAction(tr("Spatial Join…"), lambda: _run_alg("native:joinattributesbylocation", {"INPUT": layer}))
            joins.addAction(tr("Remove Join(s)"), lambda: _remove_joins(layer))
            joins.addSeparator()
            joins.addAction(tr("Relate…"), related)
            continue
        if not name.startswith("@"):
            if icon and has_icon(icon):
                changes.set(action, "icon", arcmap_icon(icon))
            changes.set(action, "text", tr(caption))
            changes.set(action, "toolTip", tr(caption))
            used.add(name)
        options.addAction(action)

    button = QToolButton(toolbar)
    button.setObjectName("ArcMapTableOptionsButton")
    button.setText(tr("Table Options"))
    button.setIcon(arcmap_icon("table_options"))
    button.setMenu(options)
    button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    add(button)
    add_separator()

    pending = False
    for entry in TOOLBAR:
        if entry is None:
            pending = True
            continue
        name, icon, caption = entry
        action = resolve(name)
        if action is None or isinstance(action, QWidgetAction):
            continue
        if pending:
            add_separator()
            pending = False
        if not name.startswith("@"):
            if icon and has_icon(icon):
                changes.set(action, "icon", arcmap_icon(icon))
            changes.set(action, "toolTip", tr(caption))
            used.add(name)
        add(action)

    leftovers = [a for a in originals
                 if a.objectName() not in used and not a.isSeparator() and not isinstance(a, QWidgetAction)
                 and (a.text() or a.menu() is not None)]
    if leftovers:
        options.addSeparator()
        more = options.addMenu(tr("QGIS"))
        for a in leftovers:
            more.addAction(a)

    def undo_toolbar(toolbar=toolbar, originals=originals, button=button, custom=custom):
        if alive(toolbar):
            for a in toolbar.actions():
                if not isinstance(a, QWidgetAction) or a.defaultWidget() is button:
                    toolbar.removeAction(a)
            for i, a in enumerate(originals):
                if isinstance(a, QWidgetAction) or not alive(a):
                    continue
                before = next((w for w in originals[i + 1:] if isinstance(w, QWidgetAction) and alive(w)), None)
                if before is not None:
                    toolbar.insertAction(before, a)
                else:
                    toolbar.addAction(a)
        if alive(button):
            button.deleteLater()
        for a in custom.values():
            if alive(a):
                a.deleteLater()

    changes.add(undo_toolbar)

    # --- context menus
    menus = TableMenus(dialog, layer, dual, iface, by_name)
    menus_holder["menus"] = menus
    changes.add(menus.stop)

    # --- footer
    layout = dialog.layout()
    footer = TableFooter(dialog, layer, dual)
    if isinstance(layout, QVBoxLayout):
        layout.addWidget(footer)
    else:
        try:
            layout.addWidget(footer, layout.rowCount(), 0, 1, max(1, layout.columnCount()))
        except Exception:  # noqa: BLE001
            layout.addWidget(footer)
    changes.add(footer.remove)
    for view in dialog.findChildren(QWidget):
        if view.metaObject().className() in ("QgsAttributeTableView", "QTableView"):
            changes.set(view, "alternatingRowColors", True)

    # --- docked Table window: tab named after the layer
    dock = dialog.parent()
    if isinstance(dock, QDockWidget):
        from .panes import TitleKeeper

        changes.set(dock, "windowTitle", layer.name())
        keeper = TitleKeeper(dock, layer.name())
        changes.add(keeper.stop)


def _run_alg(alg, params):
    try:
        from processing import execAlgorithmDialog

        execAlgorithmDialog(alg, params)
    except ImportError:
        pass


def _remove_joins(layer):
    for join in list(layer.vectorJoins()):
        layer.removeJoin(join.joinLayerId())
    layer.triggerRepaint()


def dock_tables(changes):
    """ArcMap keeps tables in one docked, tabbed Table window."""
    settings = QgsSettings()
    key = "qgis/dockAttributeTable"
    previous = settings.value(key)
    settings.setValue(key, True)

    def undo(previous=previous):
        s = QgsSettings()
        if previous is None:
            s.remove(key)
        else:
            s.setValue(key, previous)

    changes.add(undo)
