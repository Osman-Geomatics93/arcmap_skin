# -*- coding: utf-8 -*-
"""ArcMap-style defaults: pastel random fills with a grey outline, cyan
selection, Arial 10 labels and a set of ArcMap-like colour ramps.

New vector layers whose renderer is still QGIS's default single symbol get
an ArcMap symbol. The colour scheme is registered as the project's random
style colour scheme. All of it is reverted on undo.
"""

import json
import os

from qgis.core import (
    Qgis,
    QgsColorScheme,
    QgsFillSymbol,
    QgsGradientColorRamp,
    QgsGradientStop,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsPresetSchemeColorRamp,
    QgsProject,
    QgsSingleSymbolRenderer,
    QgsStyle,
    QgsTextFormat,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QColor, QFont

from .util import RESOURCES, alive, log_ignored, tr

TAG = "ArcMap"
PREFIX = "ArcMap "
SELECTION = QColor(0, 255, 255)
OUTLINE = QColor(110, 110, 110)

# ArcMap's "random" fills are muted pastels.
PASTELS = [
    "#BEE8FF", "#FFEBAF", "#D3FFBE", "#FFBEBE", "#E1E1E1", "#FFD37F",
    "#E8BEFF", "#BEFFE8", "#FFFFBE", "#CDAA66", "#A3FF73", "#FFBEE8",
    "#BED2FF", "#FFEBBE", "#D7C29E", "#E9FFBE", "#FFA77F", "#C29ED7",
]


class ArcMapColorScheme(QgsColorScheme):
    def __init__(self):
        super().__init__()

    def schemeName(self):  # noqa: N802
        return tr("ArcMap Pastels")

    def flags(self):
        return QgsColorScheme.SchemeFlag.ShowInAllContexts

    def fetchColors(self, context="", baseColor=QColor()):  # noqa: N802,N803
        return [(QColor(c), c) for c in PASTELS]

    def clone(self):
        return ArcMapColorScheme()


def arcmap_symbol(geometry_type, color):
    if geometry_type == Qgis.GeometryType.Polygon:
        symbol = QgsFillSymbol.createSimple({
            "color": color.name(),
            "outline_color": OUTLINE.name(),
            "outline_width": "0.4",
            "outline_width_unit": "Point",
            "style": "solid",
        })
    elif geometry_type == Qgis.GeometryType.Line:
        symbol = QgsLineSymbol.createSimple({
            "line_color": _line_color(color).name(),
            "line_width": "1",
            "line_width_unit": "Point",
            "capstyle": "round",
            "joinstyle": "round",
        })
    else:
        symbol = QgsMarkerSymbol.createSimple({
            "name": "circle",
            "color": _line_color(color).name(),
            "outline_color": OUTLINE.name(),
            "outline_width": "0.4",
            "outline_width_unit": "Point",
            "size": "4",
            "size_unit": "Point",
        })
    return symbol


def _line_color(color):
    """Lines and points use a saturated version of the pastel."""
    h, s, v, a = color.getHsvF()
    return QColor.fromHsvF(h, min(1.0, s + 0.45), max(0.0, v - 0.25), a)


def arcmap_text_format():
    fmt = QgsTextFormat()
    fmt.setFont(QFont("Arial"))
    fmt.setSize(10)
    try:
        from qgis.core import Qgis

        fmt.setSizeUnit(Qgis.RenderUnit.Points)
    except AttributeError:  # QGIS < 3.30
        from qgis.core import QgsUnitTypes

        fmt.setSizeUnit(QgsUnitTypes.RenderPoints)
    fmt.setColor(QColor(0, 0, 0))
    return fmt


def _is_default_single_symbol(layer):
    renderer = layer.renderer()
    if not isinstance(renderer, QgsSingleSymbolRenderer):
        return False
    symbol = renderer.symbol()
    if symbol is None or symbol.symbolLayerCount() != 1:
        return False
    sl = symbol.symbolLayer(0)
    props = sl.properties()
    # QGIS default: random colour already applied, standard widths/sizes.
    gt = layer.geometryType()
    if gt == Qgis.GeometryType.Polygon:
        return props.get("outline_width") in ("0.26", "0.26000000000000001") and props.get("style") == "solid"
    if gt == Qgis.GeometryType.Line:
        return props.get("line_width") in ("0.26", "0.26000000000000001")
    return props.get("size") in ("2", "2.0") and props.get("name") == "circle"


def load_ramps():
    path = os.path.join(RESOURCES, "color_ramps.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    ramps = {}
    for entry in data:
        name = PREFIX + entry["name"]
        if "stops" in entry:
            stops = entry["stops"]
            ramp = QgsGradientColorRamp(QColor(stops[0][1]), QColor(stops[-1][1]))
            mids = [QgsGradientStop(float(o), QColor(c)) for o, c in stops[1:-1]]
            ramp.setStops(mids)
            ramp.setDiscrete(bool(entry.get("discrete", False)))
        elif "colors" in entry:
            ramp = QgsPresetSchemeColorRamp([QColor(c) for c in entry["colors"]])
        else:
            continue
        ramps[name] = ramp
    ramps[PREFIX + "Pastels"] = QgsPresetSchemeColorRamp([QColor(c) for c in PASTELS])
    return ramps


class Symbology:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.project = QgsProject.instance()
        self.scheme = ArcMapColorScheme()
        self.previous_selection = self.canvas.selectionColor()
        self.added_ramps = []
        self._tagged = []
        style = self.project.styleSettings()
        self.prev_text_format = QgsTextFormat(style.defaultTextFormat())
        self.prev_random_scheme = style.randomizeDefaultSymbolColor()
        self._apply()

    def _apply(self):
        from qgis.core import QgsApplication

        registry = QgsApplication.colorSchemeRegistry()
        registry.addColorScheme(self.scheme)
        try:
            registry.setRandomStyleColorScheme(self.scheme)
        except (AttributeError, TypeError) as exc:
            log_ignored("setRandomStyleColorScheme", exc)
        self.set_project_defaults()
        self.set_selection_color()
        self.project.readProject.connect(self._project_read)
        self.project.cleared.connect(self.set_project_defaults)
        self.project.layersAdded.connect(self.restyle)
        self.add_ramps()

    def _keep_clean(self, func):
        """Run ``func`` without leaving the project marked as modified."""
        dirty = self.project.isDirty()
        func()
        if not dirty:
            self.project.setDirty(False)
            QTimer.singleShot(0, lambda: self.project.setDirty(False) if alive(self.canvas) else None)

    def set_project_defaults(self):
        style = self.project.styleSettings()
        self._keep_clean(lambda: style.setDefaultTextFormat(arcmap_text_format()))

    def _project_read(self, *_):
        QTimer.singleShot(0, self.set_selection_color)
        QTimer.singleShot(0, self.set_project_defaults)

    def set_selection_color(self):
        if alive(self.canvas):
            self.canvas.setSelectionColor(SELECTION)
            self._keep_clean(lambda: self.project.setSelectionColor(SELECTION))

    def restyle(self, layers):
        from qgis.core import QgsApplication

        for layer in layers:
            if not isinstance(layer, QgsVectorLayer) or not layer.isSpatial():
                continue
            if not _is_default_single_symbol(layer):
                continue
            color = QgsApplication.colorSchemeRegistry().fetchRandomStyleColor()
            if not color.isValid():
                color = QColor(PASTELS[0])
            layer.setRenderer(QgsSingleSymbolRenderer(arcmap_symbol(layer.geometryType(), color)))
            layer.triggerRepaint()

    def add_ramps(self):
        style = QgsStyle.defaultStyle()
        existing = set(style.colorRampNames())
        for name, ramp in load_ramps().items():
            if name not in existing:
                if style.addColorRamp(name, ramp, True):
                    self.added_ramps.append(name)
            if TAG not in style.tagsOfSymbol(QgsStyle.StyleEntity.ColorrampEntity, name):
                style.tagSymbol(QgsStyle.StyleEntity.ColorrampEntity, name, [TAG])
                self._tagged.append(name)

    def undo(self):
        from qgis.core import QgsApplication

        for signal, slot in (
            (self.project.readProject, self._project_read),
            (self.project.cleared, self.set_project_defaults),
            (self.project.layersAdded, self.restyle),
        ):
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        if alive(self.canvas):
            self.canvas.setSelectionColor(self.previous_selection)
            self.project.setSelectionColor(self.previous_selection)
        style = self.project.styleSettings()
        self._keep_clean(lambda: style.setDefaultTextFormat(self.prev_text_format))
        registry = QgsApplication.colorSchemeRegistry()
        try:
            registry.setRandomStyleColorScheme(None)
        except (AttributeError, TypeError) as exc:
            log_ignored("setRandomStyleColorScheme(None)", exc)
        registry.removeColorScheme(self.scheme)
        qstyle = QgsStyle.defaultStyle()
        for name in self.added_ramps:
            qstyle.removeColorRamp(name)
        for name in self._tagged:
            if name not in self.added_ramps:
                qstyle.detagSymbol(QgsStyle.StyleEntity.ColorrampEntity, name, [TAG])
        try:
            qstyle.remove(QgsStyle.StyleEntity.TagEntity, qstyle.tagId(TAG))
        except (AttributeError, TypeError, RuntimeError) as exc:
            log_ignored("remove tag", exc)


def apply_symbology(iface, changes):
    sym = Symbology(iface)
    changes.add(sym.undo)
    return sym
