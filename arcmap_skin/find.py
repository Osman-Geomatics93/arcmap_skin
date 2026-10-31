# -*- coding: utf-8 -*-
"""ArcMap's Find window: *Features* (search attribute values in a layer or
all layers) and *Locations* (geocode a place name with Nominatim).
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeatureRequest,
    QgsGeometry,
    QgsProject,
    QgsVectorLayer,
)
from qgis.gui import QgsMapLayerComboBox
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .util import arcmap_icon, tr

ID_ROLE = Qt.ItemDataRole.UserRole + 5


class FindDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.setObjectName("ArcMapFindDialog")
        self.setWindowTitle(tr("Find"))
        self.setWindowIcon(arcmap_icon("find"))
        self.resize(560, 460)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs, 1)
        self.tabs.addTab(self._features_tab(), tr("Features"))
        self.tabs.addTab(self._locations_tab(), tr("Locations"))

    # ----------------------------------------------------------- features

    def _features_tab(self):
        page = QWidget(self)
        form = QFormLayout(page)
        self.text = QLineEdit(page)
        self.text.returnPressed.connect(self.find_features)
        form.addRow(tr("Find:"), self.text)
        self.layer_box = QgsMapLayerComboBox(page)
        from .query_builder import _vector_filter

        self.layer_box.setFilters(_vector_filter())
        self.layer_box.setAllowEmptyLayer(True, tr("<All layers>"))
        form.addRow(tr("In:"), self.layer_box)
        self.field_box = QComboBox(page)
        self.layer_box.layerChanged.connect(self._fill_fields)
        self._fill_fields(self.layer_box.currentLayer())
        form.addRow(tr("In field:"), self.field_box)
        self.whole = QCheckBox(tr("Find features that are similar to or contain the search string"), page)
        self.whole.setChecked(True)
        form.addRow(self.whole)
        row = QHBoxLayout()
        find = QPushButton(tr("Find"), page)
        find.setDefault(True)
        find.clicked.connect(self.find_features)
        new = QPushButton(tr("New Search"), page)
        new.clicked.connect(self._clear_features)
        row.addWidget(find)
        row.addWidget(new)
        row.addStretch(1)
        form.addRow(row)
        self.results = QTableWidget(0, 3, page)
        self.results.setHorizontalHeaderLabels([tr("Value"), tr("Layer"), tr("Field")])
        self.results.horizontalHeader().setStretchLastSection(True)
        self.results.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results.itemClicked.connect(self._flash)
        self.results.itemDoubleClicked.connect(self._zoom)
        form.addRow(self.results)
        self.status = QLabel("", page)
        form.addRow(self.status)
        hint = QLabel(tr("Click a result to flash it, double-click to zoom and select it."), page)
        hint.setWordWrap(True)
        form.addRow(hint)
        return page

    def _fill_fields(self, layer):
        self.field_box.clear()
        self.field_box.addItem(tr("<All fields>"), "")
        if isinstance(layer, QgsVectorLayer):
            for f in layer.fields():
                self.field_box.addItem(f.name(), f.name())

    def _clear_features(self):
        self.text.clear()
        self.results.setRowCount(0)
        self.status.clear()

    def _layers(self):
        layer = self.layer_box.currentLayer()
        if isinstance(layer, QgsVectorLayer):
            return [layer]
        return [lyr for lyr in QgsProject.instance().mapLayers().values() if isinstance(lyr, QgsVectorLayer)]

    def find_features(self):
        text = self.text.text().strip()
        self.results.setRowCount(0)
        if not text:
            return
        field = self.field_box.currentData() or ""
        contains = self.whole.isChecked()
        needle = text.lower()
        count = 0
        for layer in self._layers():
            fields = [field] if field and layer.fields().indexOf(field) >= 0 else [f.name() for f in layer.fields()]
            request = QgsFeatureRequest().setFlags(QgsFeatureRequest.Flag.NoGeometry)
            for feat in layer.getFeatures(request):
                for name in fields:
                    value = feat[name]
                    if value is None:
                        continue
                    s = str(value)
                    if (needle in s.lower()) if contains else (s.lower() == needle):
                        row = self.results.rowCount()
                        self.results.insertRow(row)
                        item = QTableWidgetItem(s)
                        item.setData(ID_ROLE, (layer.id(), feat.id()))
                        self.results.setItem(row, 0, item)
                        self.results.setItem(row, 1, QTableWidgetItem(layer.name()))
                        self.results.setItem(row, 2, QTableWidgetItem(name))
                        count += 1
                        break
                if count >= 2000:
                    break
        self.status.setText(tr("%d object(s) found") % count)

    def _target(self, item):
        data = self.results.item(item.row(), 0).data(ID_ROLE)
        if not data:
            return None, None
        layer = QgsProject.instance().mapLayer(data[0])
        return layer, data[1]

    def _flash(self, item):
        layer, fid = self._target(item)
        if layer is not None:
            self.iface.mapCanvas().flashFeatureIds(layer, [fid])

    def _zoom(self, item):
        layer, fid = self._target(item)
        if layer is None:
            return
        QTimer.singleShot(0, lambda: self._zoom_now(layer, fid))

    def _zoom_now(self, layer, fid):
        layer.selectByIds([fid])
        self.iface.setActiveLayer(layer)
        self.iface.mapCanvas().zoomToSelected(layer)

    # ---------------------------------------------------------- locations

    def _locations_tab(self):
        page = QWidget(self)
        form = QFormLayout(page)
        self.place = QLineEdit(page)
        self.place.setPlaceholderText(tr("Place name or address"))
        self.place.returnPressed.connect(self.find_places)
        form.addRow(tr("Find:"), self.place)
        row = QHBoxLayout()
        find = QPushButton(tr("Find"), page)
        find.clicked.connect(self.find_places)
        row.addWidget(find)
        row.addStretch(1)
        form.addRow(row)
        self.places = QTableWidget(0, 1, page)
        self.places.setHorizontalHeaderLabels([tr("Location")])
        self.places.horizontalHeader().setStretchLastSection(True)
        self.places.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.places.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.places.itemDoubleClicked.connect(self._zoom_place)
        form.addRow(self.places)
        self.place_status = QLabel(tr("Powered by OpenStreetMap Nominatim"), page)
        form.addRow(self.place_status)
        return page

    def find_places(self):
        text = self.place.text().strip()
        self.places.setRowCount(0)
        if not text:
            return
        try:
            from qgis.core import QgsGeocoderContext, QgsNominatimGeocoder

            geocoder = QgsNominatimGeocoder()
            ctx = QgsGeocoderContext(QgsProject.instance().transformContext())
            results = geocoder.geocodeString(text, ctx)
        except Exception as exc:  # noqa: BLE001
            self.place_status.setText(tr("Geocoding failed: %s") % exc)
            return
        for res in results:
            row = self.places.rowCount()
            self.places.insertRow(row)
            item = QTableWidgetItem(res.identifier())
            item.setData(ID_ROLE, (res.geometry().asWkt(), res.crs().authid(), res.viewport().toString()))
            self.places.setItem(row, 0, item)
        self.place_status.setText(tr("%d location(s) found") % len(results))

    def _zoom_place(self, item):
        data = item.data(ID_ROLE)
        if not data:
            return
        wkt, authid, _viewport = data
        geom = QgsGeometry.fromWkt(wkt)
        canvas = self.iface.mapCanvas()
        src = QgsCoordinateReferenceSystem(authid or "EPSG:4326")
        xform = QgsCoordinateTransform(src, canvas.mapSettings().destinationCrs(), QgsProject.instance())
        geom.transform(xform)
        point = geom.asPoint() if geom.type() == 0 else geom.centroid().asPoint()
        canvas.setCenter(point)
        if canvas.scale() > 50000:
            canvas.zoomScale(25000)
        canvas.refresh()
        canvas.flashGeometries([geom], canvas.mapSettings().destinationCrs())


_dialog = None


def open_find(iface):
    global _dialog
    if _dialog is None or not _dialog.isVisible():
        _dialog = FindDialog(iface)
    _dialog.show()
    _dialog.raise_()
    _dialog.activateWindow()
    _dialog.text.setFocus()
    return _dialog
