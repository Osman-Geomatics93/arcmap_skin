# -*- coding: utf-8 -*-
"""ArcMap's *Getting Started* dialog: Existing Maps (recent, browse) and
New Maps (blank map, project templates). Shown at start-up while the look
is on and no project is loaded; can be switched off from the dialog.
"""

import os

from qgis.core import QgsApplication, QgsProject, QgsSettings
from qgis.PyQt.QtCore import QSize, Qt, QTimer
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .util import SETTINGS_GROUP, arcmap_icon, find_action, tr

KEY_SHOW = SETTINGS_GROUP + "/show_getting_started"
PATH_ROLE = Qt.ItemDataRole.UserRole + 9


def recent_projects():
    settings = QgsSettings()
    settings.beginGroup("UI/recentProjects")
    out = []
    for group in sorted(settings.childGroups(), key=lambda g: int(g) if g.isdigit() else 0):
        settings.beginGroup(group)
        path = settings.value("path", "")
        title = settings.value("title", "") or os.path.basename(path)
        settings.endGroup()
        if path and os.path.exists(path):
            out.append((title, path))
    settings.endGroup()
    return out


def template_projects():
    settings = QgsSettings()
    folder = settings.value("qgis/projectTemplateDir", "") or os.path.join(QgsApplication.qgisSettingsDirPath(), "project_templates")
    out = []
    if folder and os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith((".qgs", ".qgz")):
                out.append((os.path.splitext(name)[0], os.path.join(folder, name)))
    return out


class GettingStartedDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.setObjectName("ArcMapGettingStarted")
        self.setWindowTitle(tr("ArcMap Skin – Getting Started"))
        self.setWindowIcon(arcmap_icon("new_map"))
        self.resize(760, 480)
        layout = QVBoxLayout(self)
        split = QSplitter(self)
        layout.addWidget(split, 1)

        self.tree = QTreeWidget(split)
        self.tree.setHeaderHidden(True)
        existing = QTreeWidgetItem(self.tree, [tr("Existing Maps")])
        existing.setIcon(0, arcmap_icon("open"))
        self.recent_item = QTreeWidgetItem(existing, [tr("Recent")])
        self.browse_item = QTreeWidgetItem(existing, [tr("Browse for more…")])
        new = QTreeWidgetItem(self.tree, [tr("New Maps")])
        new.setIcon(0, arcmap_icon("new_map"))
        self.blank_item = QTreeWidgetItem(new, [tr("My Templates")])
        self.templates_item = QTreeWidgetItem(new, [tr("Templates")])
        self.tree.expandAll()
        self.tree.currentItemChanged.connect(self._section_changed)

        right = QVBoxLayout()
        panel = QWidget(split)
        panel.setLayout(right)
        self.title = QLabel("", panel)
        self.title.setObjectName("ArcMapGettingStartedTitle")
        right.addWidget(self.title)
        self.list = QListWidget(panel)
        self.list.setIconSize(QSize(32, 32))
        self.list.itemDoubleClicked.connect(lambda *_: self.accept())
        right.addWidget(self.list, 1)
        self.path = QLabel("", panel)
        self.path.setWordWrap(True)
        right.addWidget(self.path)
        self.list.currentItemChanged.connect(self._item_changed)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 3)

        bottom = QHBoxLayout()
        self.dont_show = QCheckBox(tr("Do not show this dialog in the future"), self)
        bottom.addWidget(self.dont_show)
        bottom.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        for b in buttons.buttons():
            b.setAutoDefault(False)
            b.setDefault(False)
        bottom.addWidget(buttons)
        layout.addLayout(bottom)
        self.tree.setCurrentItem(self.recent_item)

    def _section_changed(self, current, previous):
        self.list.clear()
        self.path.clear()
        if current is self.recent_item:
            self.title.setText(tr("Open existing map"))
            for title, path in recent_projects():
                item = QListWidgetItem(arcmap_icon("map_properties"), title)
                item.setData(PATH_ROLE, path)
                item.setToolTip(path)
                self.list.addItem(item)
            if not self.list.count():
                self.list.addItem(QListWidgetItem(tr("(no recent maps)")))
        elif current is self.browse_item:
            self.title.setText(tr("Browse for an existing map"))
            item = QListWidgetItem(arcmap_icon("open"), tr("Browse for more…"))
            item.setData(PATH_ROLE, "::browse")
            self.list.addItem(item)
        elif current is self.blank_item:
            self.title.setText(tr("New map"))
            item = QListWidgetItem(arcmap_icon("new_map"), tr("Blank Map"))
            item.setData(PATH_ROLE, "::blank")
            self.list.addItem(item)
        elif current is self.templates_item:
            self.title.setText(tr("Create a map from a template"))
            for title, path in template_projects():
                item = QListWidgetItem(arcmap_icon("layout_view"), title)
                item.setData(PATH_ROLE, path)
                self.list.addItem(item)
            if not self.list.count():
                self.list.addItem(QListWidgetItem(tr("(no templates – save a project in the project_templates folder)")))
        # Nothing preselected: Open does nothing until the user picks an item.
        self.list.setCurrentRow(-1)

    def _item_changed(self, current, previous):
        target = current.data(PATH_ROLE) if current else None
        self.path.setText(target if target and not str(target).startswith("::") else "")

    def accept(self):
        item = self.list.currentItem()
        if self.dont_show.isChecked():
            QgsSettings().setValue(KEY_SHOW, False)
        target = item.data(PATH_ROLE) if item is not None else None
        super().accept()
        if not target:
            return
        # The dialog deletes itself on close and loading a project processes
        # events, so run the action only after the current (double-click)
        # event has fully finished. Doing it inline crashed QGIS.
        iface = self.iface
        QTimer.singleShot(0, lambda: _open_target(iface, target))

    def reject(self):
        if self.dont_show.isChecked():
            QgsSettings().setValue(KEY_SHOW, False)
        super().reject()


def _open_target(iface, target):
    if target == "::browse":
        action = find_action(iface.mainWindow(), "mActionOpenProject")
        if action is not None:
            action.trigger()
    elif target == "::blank":
        iface.newProject(False)
    else:
        iface.addProject(target)


def maybe_show(iface):
    """Show the dialog at start-up when enabled and no project is loaded."""
    if not QgsSettings().value(KEY_SHOW, True, type=bool):
        return None
    project = QgsProject.instance()
    if project.fileName() or project.mapLayers():
        return None
    dlg = GettingStartedDialog(iface)
    dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dlg.show()
    return dlg


def show(iface):
    dlg = GettingStartedDialog(iface)
    dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dlg.show()
    return dlg
