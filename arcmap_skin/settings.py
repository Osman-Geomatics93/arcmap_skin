# -*- coding: utf-8 -*-
"""Feature switches and the "ArcMap Skin" page in QGIS's Options dialog.

Every part of the look can be switched off individually (a user may want
the ArcMap layout without, say, the symbology defaults or the keyboard
shortcuts). Switches live in QgsSettings under ``arcmap_skin/feature/<key>``
and default to on. Changing them re-applies the look.
"""

from qgis.core import QgsSettings
from qgis.gui import QgsOptionsPageWidget, QgsOptionsWidgetFactory
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox, QLabel,
                                 QVBoxLayout)

from .util import SETTINGS_GROUP, tr, ui_icon

FEATURE_PREFIX = SETTINGS_GROUP + "/feature/"
KEY_THEME = SETTINGS_GROUP + "/theme"

# key → (caption, description)
FEATURES = [
    ("icon_theme", "Icon theme", "Redraw QGIS icons in the ArcMap style (layer icons need a restart)"),
    ("menus", "ArcMap menu bar", "File, Edit, View, Bookmarks, Insert, Selection, Geoprocessing, Customize, Windows, Help"),
    ("toolbars", "ArcMap toolbars", "Standard, Tools, Editor, Draw, Labeling, Layout… built from QGIS commands"),
    ("panes", "Table Of Contents and panes", "List By views, Catalog, ArcToolbox, Search, pane titles"),
    ("toc_menu", "ArcMap right-click menu in the Table Of Contents", ""),
    ("map_frame", "ArcMap status bar and Data/Layout View buttons", "Replaces the QGIS status bar"),
    ("dialogs", "ArcMap Table window and Layer Properties tabs", "Attribute table, layer / project / options dialogs"),
    ("arctoolbox", "ArcToolbox pane", "Every Processing tool in ArcMap toolboxes"),
    ("editing", "ArcMap editing", "Start/Stop Editing, Create Features, Snapping toolbar, Edit Tool, Attributes window"),
    ("label_manager", "Label Manager and Labeling toolbar", ""),
    ("layout_designer", "ArcMap Layout View", "Insert menu and Layout toolbar in the layout designer"),
    ("symbology", "ArcMap symbology defaults", "Pastel fills, cyan selection, Arial labels, ArcMap colour ramps"),
    ("shortcuts", "ArcMap keyboard shortcuts", "Z zoom in, X zoom out, C pan, S select, I identify"),
    ("canvas_menu", "ArcMap right-click menu on the map", ""),
    ("basemaps", "Add Basemap gallery", ""),
    ("getting_started", "Getting Started dialog at start-up", ""),
]
THEMES = [("arcmap_light", "ArcMap (light)"), ("arcmap_dark", "ArcMap (dark)")]


def enabled(key):
    return QgsSettings().value(FEATURE_PREFIX + key, True, type=bool)


def set_enabled(key, on):
    QgsSettings().setValue(FEATURE_PREFIX + key, bool(on))


def theme():
    value = QgsSettings().value(KEY_THEME, "arcmap_light", type=str)
    return value if value in dict(THEMES) else "arcmap_light"


class SettingsPage(QgsOptionsPageWidget):
    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setObjectName("mOptionsPageArcMapSkin")
        layout = QVBoxLayout(self)
        intro = QLabel(tr("Choose which parts of the ArcMap look are applied. Changes take effect when you click OK or Apply."), self)
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.theme_box = QComboBox(self)
        for key, caption in THEMES:
            self.theme_box.addItem(tr(caption), key)
        self.theme_box.setCurrentIndex(max(0, self.theme_box.findData(theme())))
        form.addRow(tr("Theme:"), self.theme_box)
        layout.addLayout(form)
        settings = QgsSettings()
        self.startup = QCheckBox(tr("Apply the ArcMap look when QGIS starts"), self)
        self.startup.setChecked(settings.value(SETTINGS_GROUP + "/enabled", True, type=bool))
        layout.addWidget(self.startup)
        group = QGroupBox(tr("Features"), self)
        glayout = QVBoxLayout(group)
        self.boxes = {}
        for key, caption, description in FEATURES:
            box = QCheckBox(tr(caption), group)
            if description:
                box.setToolTip(tr(description))
            box.setChecked(enabled(key))
            glayout.addWidget(box)
            self.boxes[key] = box
        layout.addWidget(group)
        layout.addStretch(1)

    def apply(self):
        settings = QgsSettings()
        changed = False
        for key, box in self.boxes.items():
            if enabled(key) != box.isChecked():
                set_enabled(key, box.isChecked())
                changed = True
        new_theme = self.theme_box.currentData()
        if new_theme != theme():
            settings.setValue(KEY_THEME, new_theme)
            changed = True
        settings.setValue(SETTINGS_GROUP + "/enabled", self.startup.isChecked())
        if changed and self.plugin is not None and self.plugin.on:
            # QGIS is still saving the other Options pages (some of them pop
            # up message boxes); the look is re-applied only once every
            # modal dialog, including the Options dialog itself, has closed.
            self.plugin.reapply_when_idle()


class SettingsDialog(QDialog):
    """ArcMap Skin Options as its own window.

    The page is also registered in the QGIS Options dialog, but opening that
    dialog validates every other page on OK (Processing complains about a
    missing output folder, for instance), so the ArcMap menu entry opens
    this lighter dialog instead.
    """

    def __init__(self, plugin, parent=None):
        super().__init__(parent)
        self.setObjectName("ArcMapSkinOptions")
        self.setWindowTitle(tr("ArcMap Skin Options"))
        self.setWindowIcon(ui_icon("icon"))
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        layout = QVBoxLayout(self)
        self.page = SettingsPage(plugin, self)
        layout.addWidget(self.page, 1)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.page.apply)
        layout.addWidget(buttons)
        self.resize(460, 560)

    # QDialog.closeEvent() calls reject(), so neither override may call
    # close(); hide through the base class and let the window delete itself.
    def accept(self):
        self.page.apply()
        super().accept()
        self.deleteLater()

    def reject(self):
        super().reject()
        self.deleteLater()


def show_options_dialog(plugin, parent):
    """Show (or raise) the ArcMap Skin Options window."""
    for w in parent.findChildren(QDialog, "ArcMapSkinOptions"):
        if not w.isVisible():
            continue  # closed, deferred delete still pending
        w.raise_()
        w.activateWindow()
        return w
    dialog = SettingsDialog(plugin, parent)
    dialog.show()
    return dialog


class SettingsFactory(QgsOptionsWidgetFactory):
    def __init__(self, plugin):
        super().__init__(tr("ArcMap Skin"), ui_icon("icon"))
        self.plugin = plugin

    def createWidget(self, parent):  # noqa: N802
        return SettingsPage(self.plugin, parent)
