# -*- coding: utf-8 -*-
"""A small modal progress box shown while the look is switched on or off."""

from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from .util import tr


class ProgressBox(QWidget):
    """Frameless progress window with a title and a 0–1000 bar."""

    def __init__(self, parent, title):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("ArcMapProgress")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        self.label = QLabel(title, self)
        self.label.setObjectName("ArcMapProgressTitle")
        self.step = QLabel("", self)
        self.bar = QProgressBar(self)
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        layout.addWidget(self.label)
        layout.addWidget(self.step)
        layout.addWidget(self.bar)
        self._base = 0.0
        self._span = 1.0
        if parent is not None:
            geo = parent.geometry()
            self.move(geo.center().x() - 180, geo.center().y() - 50)
        self.show()
        QCoreApplication.processEvents()

    def begin(self, text, base, span):
        """Start a weighted step covering ``base``..``base+span`` of the bar."""
        self.step.setText(text)
        self._base = base
        self._span = span
        self.fraction(0.0)

    def fraction(self, f):
        self.bar.setValue(int(1000 * (self._base + self._span * max(0.0, min(1.0, f)))))
        QCoreApplication.processEvents()

    def finish(self):
        self.bar.setValue(1000)
        QCoreApplication.processEvents()
        self.close()


def weighted(steps):
    """Yield (name, callback, base, span) for ``[(name, weight, callback), …]``."""
    total = float(sum(w for _, w, _ in steps)) or 1.0
    base = 0.0
    for name, weight, callback in steps:
        span = weight / total
        yield name, callback, base, span
        base += span


def _(text):
    return tr(text)
