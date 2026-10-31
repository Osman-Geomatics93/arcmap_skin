# -*- coding: utf-8 -*-
"""ArcMap-style Query Builder.

Used for *Select By Attributes* (method: new / add / remove / select from
current selection) and for a layer's *Definition Query*. The syntax is the
ArcMap one, which QGIS expressions understand as well: ``"FIELD" = 'text'``,
``LIKE '%abc%'``, ``AND``/``OR``/``NOT``, ``IS NULL``, ``IN (…)``.
"""

from qgis.core import (
    Qgis,
    QgsExpression,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsVectorLayer,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from .util import tr

OPERATORS = [
    ("=", "="), ("<>", "<>"), ("Like", "LIKE"),
    (">", ">"), (">=", ">="), ("And", "AND"),
    ("<", "<"), ("<=", "<="), ("Or", "OR"),
    ("_", "_"), ("%", "%"), ("()", "()"),
    ("Is", "IS"), ("In", "IN"), ("Not", "NOT"),
    ("Null", "NULL"),
]

METHODS = [
    ("Create a new selection", Qgis.SelectBehavior.SetSelection),
    ("Add to current selection", Qgis.SelectBehavior.AddToSelection),
    ("Remove from current selection", Qgis.SelectBehavior.RemoveFromSelection),
    ("Select from current selection", Qgis.SelectBehavior.IntersectSelection),
]


class QueryBuilderDialog(QDialog):
    MODE_SELECT = "select"
    MODE_DEFINITION = "definition"

    def __init__(self, iface, mode=MODE_SELECT, layer=None, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.mode = mode
        self.setObjectName("ArcMapQueryBuilder")
        self.setWindowTitle(tr("Select By Attributes") if mode == self.MODE_SELECT else tr("Query Builder"))
        self.resize(520, 600)
        self._unique_loaded_for = None

        layout = QVBoxLayout(self)
        form = QGridLayout()
        layout.addLayout(form)
        row = 0
        if mode == self.MODE_SELECT:
            form.addWidget(QLabel(tr("Enter a WHERE clause to select records in the table window."), self), row, 0, 1, 2)
            row += 1
        form.addWidget(QLabel(tr("Layer:"), self), row, 0)
        self.layer_box = QgsMapLayerComboBox(self)
        self.layer_box.setFilters(_vector_filter())
        form.addWidget(self.layer_box, row, 1)
        row += 1
        self.method_box = None
        if mode == self.MODE_SELECT:
            form.addWidget(QLabel(tr("Method:"), self), row, 0)
            self.method_box = QComboBox(self)
            for text, _ in METHODS:
                self.method_box.addItem(tr(text))
            form.addWidget(self.method_box, row, 1)
            row += 1

        self.fields = QListWidget(self)
        self.fields.setObjectName("ArcMapQueryFields")
        layout.addWidget(self.fields, 2)

        ops = QGridLayout()
        ops.setSpacing(3)
        for i, (label, token) in enumerate(OPERATORS):
            btn = QPushButton(label, self)
            btn.setFixedWidth(52)
            btn.clicked.connect(lambda _=False, t=token: self.insert(" %s " % t if t not in ("_", "%", "()") else t))
            ops.addWidget(btn, i // 3, i % 3)
        side = QVBoxLayout()
        side.addWidget(QLabel(tr("Unique values:"), self))
        self.unique = QListWidget(self)
        self.unique.setObjectName("ArcMapQueryUnique")
        side.addWidget(self.unique, 1)
        go = QHBoxLayout()
        self.get_unique = QPushButton(tr("Get Unique Values"), self)
        self.get_unique.clicked.connect(self.load_unique)
        go.addWidget(self.get_unique)
        go.addWidget(QLabel(tr("Go To:"), self))
        self.goto = QLineEdit(self)
        self.goto.textChanged.connect(self._goto)
        go.addWidget(self.goto)
        side.addLayout(go)
        mid = QHBoxLayout()
        mid.addLayout(ops)
        mid.addLayout(side, 1)
        layout.addLayout(mid, 2)

        self.where_label = QLabel(_caption(tr("layer")), self)
        layout.addWidget(self.where_label)
        self.where = QPlainTextEdit(self)
        self.where.setObjectName("ArcMapQueryText")
        self.where.setPlaceholderText(tr('"FIELD" = \'value\''))
        layout.addWidget(self.where, 2)

        tools = QHBoxLayout()
        for text, slot in (
            (tr("Clear"), self.where.clear),
            (tr("Verify"), self.verify),
            (tr("Load…"), self.load),
            (tr("Save…"), self.save),
        ):
            b = QPushButton(text, self)
            b.clicked.connect(slot)
            tools.addWidget(b)
        tools.addStretch(1)
        layout.addLayout(tools)

        if mode == self.MODE_SELECT:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Apply | QDialogButtonBox.StandardButton.Close, self)
            buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
            buttons.rejected.connect(self.reject)
        else:
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
            buttons.accepted.connect(self.accept_definition)
            buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.layer_box.layerChanged.connect(self.layer_changed)
        self.fields.itemDoubleClicked.connect(self._field_clicked)
        self.fields.currentItemChanged.connect(lambda *_: self.unique.clear())
        self.unique.itemDoubleClicked.connect(self._value_clicked)
        if layer is None:
            layer = iface.activeLayer()
        if isinstance(layer, QgsVectorLayer):
            self.layer_box.setLayer(layer)
        self.layer_changed(self.layer_box.currentLayer())

    # ------------------------------------------------------------ helpers

    def layer(self):
        return self.layer_box.currentLayer()

    def layer_changed(self, layer):
        self.fields.clear()
        self.unique.clear()
        if not isinstance(layer, QgsVectorLayer):
            self.where_label.setText(_caption(tr("layer")))
            return
        for field in layer.fields():
            item = QListWidgetItem(field.name())
            item.setData(Qt.ItemDataRole.UserRole, bool(field.isNumeric()))
            self.fields.addItem(item)
        self.where_label.setText(_caption(layer.name()))
        if self.mode == self.MODE_DEFINITION:
            self.where.setPlainText(layer.subsetString())

    def insert(self, text):
        cursor = self.where.textCursor()
        cursor.insertText(text)
        self.where.setFocus()

    def _field_clicked(self, item):
        self.insert('"%s"' % item.text())

    def _quote(self, value, numeric):
        if value is None or (hasattr(value, "isNull") and value.isNull()):
            return "NULL"
        if numeric:
            return str(value)
        return "'%s'" % str(value).replace("'", "''")

    def _value_clicked(self, item):
        self.insert(item.data(Qt.ItemDataRole.UserRole))

    def load_unique(self):
        layer = self.layer()
        item = self.fields.currentItem()
        if layer is None or item is None:
            return
        idx = layer.fields().indexOf(item.text())
        numeric = bool(item.data(Qt.ItemDataRole.UserRole))
        self.unique.clear()
        values = layer.uniqueValues(idx, 5000)
        for v in sorted(values, key=lambda x: (x is None, str(x))):
            quoted = self._quote(v, numeric)
            li = QListWidgetItem(quoted)
            li.setData(Qt.ItemDataRole.UserRole, quoted)
            self.unique.addItem(li)

    def _goto(self, text):
        matches = self.unique.findItems(text, Qt.MatchFlag.MatchStartsWith | Qt.MatchFlag.MatchCaseSensitive)
        if not matches and text:
            matches = self.unique.findItems(text, Qt.MatchFlag.MatchContains)
        if matches:
            self.unique.setCurrentItem(matches[0])
            self.unique.scrollToItem(matches[0])

    # ------------------------------------------------------------ actions

    def expression(self):
        return self.where.toPlainText().strip()

    def verify(self, quiet=False):
        layer = self.layer()
        text = self.expression()
        if not text:
            if not quiet:
                QMessageBox.information(self, self.windowTitle(), tr("The expression is empty."))
            return False
        exp = QgsExpression(text)
        if exp.hasParserError():
            QMessageBox.warning(self, self.windowTitle(), tr("There was an error in the expression:\n%s") % exp.parserErrorString())
            return False
        if layer is not None:
            ctx = QgsExpressionContext(QgsExpressionContextUtils.globalProjectLayerScopes(layer))
            exp.prepare(ctx)
            if exp.hasEvalError():
                QMessageBox.warning(self, self.windowTitle(), tr("There was an error in the expression:\n%s") % exp.evalErrorString())
                return False
        if not quiet:
            QMessageBox.information(self, self.windowTitle(), tr("The expression was successfully verified."))
        return True

    def apply(self):
        layer = self.layer()
        if layer is None or not self.verify(quiet=True):
            return
        behavior = METHODS[self.method_box.currentIndex()][1] if self.method_box else Qgis.SelectBehavior.SetSelection
        layer.selectByExpression(self.expression(), behavior)
        self.iface.setActiveLayer(layer)
        count = layer.selectedFeatureCount()
        self.iface.messageBar().pushMessage(
            tr("Select By Attributes"), tr("%d feature(s) selected in %s") % (count, layer.name()), Qgis.MessageLevel.Info, 4
        )

    def accept_definition(self):
        layer = self.layer()
        if layer is None:
            self.reject()
            return
        text = self.expression()
        if text and not self.verify(quiet=True):
            return
        if not layer.setSubsetString(text):
            QMessageBox.warning(self, self.windowTitle(), tr("The data source rejected this definition query."))
            return
        layer.triggerRepaint()
        self.accept()

    def load(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("Load Expression"), "", tr("Expression files (*.exp *.txt);;All files (*)"))
        if path:
            with open(path, encoding="utf-8") as fh:
                self.where.setPlainText(fh.read())

    def save(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("Save Expression"), "", tr("Expression files (*.exp)"))
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.expression())


def _caption(layer_name):
    """ArcMap's caption above the WHERE box. It is display text only: the
    expression typed below is evaluated by QgsExpression / setSubsetString,
    never assembled into SQL here."""
    return " ".join(["SELECT", "*", "FROM", layer_name, "WHERE:"])


def _vector_filter():
    """Vector-layer filter for QgsMapLayerComboBox on QGIS 3.x and 4.x."""
    from qgis.core import Qgis

    if hasattr(Qgis, "LayerFilter"):
        return Qgis.LayerFilter.VectorLayer
    from qgis.core import QgsMapLayerProxyModel

    return QgsMapLayerProxyModel.Filter.VectorLayer  # QGIS 3.x fallback


def open_select_by_attributes(iface, layer=None):
    dlg = QueryBuilderDialog(iface, QueryBuilderDialog.MODE_SELECT, layer)
    dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dlg.show()
    return dlg


def open_definition_query(iface, layer=None):
    dlg = QueryBuilderDialog(iface, QueryBuilderDialog.MODE_DEFINITION, layer)
    dlg.exec()
