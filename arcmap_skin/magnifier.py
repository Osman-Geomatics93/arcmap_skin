# -*- coding: utf-8 -*-
"""ArcMap's Magnifier window: a floating map that follows the mouse and
shows the area under the cursor at 400 % (changeable)."""

from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QColor, QPainter, QPen
from qgis.PyQt.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QVBoxLayout

from .util import alive, arcmap_icon, tr

FACTORS = [200, 400, 800, 1000]


class Crosshair(QLabel):
    """Transparent overlay drawing the centre crosshair over the magnifier."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet("background: transparent")

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setPen(QPen(QColor(220, 40, 40), 1))
        w, h = self.width(), self.height()
        p.drawLine(w // 2 - 12, h // 2, w // 2 + 12, h // 2)
        p.drawLine(w // 2, h // 2 - 12, w // 2, h // 2 + 12)
        p.end()


class MagnifierWindow(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow(), Qt.WindowType.Tool)
        self.iface = iface
        self.main = iface.mapCanvas()
        self.setObjectName("ArcMapMagnifier")
        self.setWindowTitle(tr("Magnifier"))
        self.setWindowIcon(arcmap_icon("zoom_in"))
        self.resize(320, 300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        top = QHBoxLayout()
        top.addWidget(QLabel(tr("Magnification:"), self))
        self.factor = QComboBox(self)
        for f in FACTORS:
            self.factor.addItem("%d%%" % f, f)
        self.factor.setCurrentIndex(1)
        self.factor.currentIndexChanged.connect(lambda *_: self.update_view())
        top.addWidget(self.factor)
        top.addStretch(1)
        layout.addLayout(top)
        self.canvas = QgsMapCanvas(self)
        self.canvas.setCanvasColor(self.main.canvasColor())
        self.canvas.setDestinationCrs(self.main.mapSettings().destinationCrs())
        self.canvas.setLayers(self.main.layers())
        self.canvas.enableAntiAliasing(True)
        self.canvas.setParallelRenderingEnabled(True)
        layout.addWidget(self.canvas, 1)
        self.cross = Crosshair(self.canvas)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._refresh)
        self._point = None
        self.main.xyCoordinates.connect(self._moved)
        self.main.layersChanged.connect(self._layers_changed)
        self.main.destinationCrsChanged.connect(self._crs_changed)
        self._point = self.main.center()
        self.update_view()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self.cross.setGeometry(self.canvas.rect())

    def _moved(self, point):
        self._point = point
        self._timer.start()

    def _layers_changed(self):
        if alive(self.canvas):
            self.canvas.setLayers(self.main.layers())

    def _crs_changed(self):
        if alive(self.canvas):
            self.canvas.setDestinationCrs(self.main.mapSettings().destinationCrs())

    def _refresh(self):
        self.update_view()

    def update_view(self):
        if not alive(self.canvas) or self._point is None:
            return
        factor = self.factor.currentData() or 400
        self.canvas.zoomScale(self.main.scale() * 100.0 / factor)
        self.canvas.setCenter(self._point)
        self.canvas.refresh()
        self.cross.setGeometry(self.canvas.rect())

    def closeEvent(self, event):  # noqa: N802
        for signal, slot in ((self.main.xyCoordinates, self._moved), (self.main.layersChanged, self._layers_changed),
                             (self.main.destinationCrsChanged, self._crs_changed)):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        super().closeEvent(event)


_window = None


def open_magnifier(iface):
    global _window
    if _window is None or not alive(_window) or not _window.isVisible():
        _window = MagnifierWindow(iface)
        _window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    _window.show()
    _window.raise_()
    return _window
