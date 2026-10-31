# -*- coding: utf-8 -*-
"""ArcMap's Customize dialog: Toolbars (show/hide), Commands (find any
command and add it to a toolbar) and Options (keyboard, interface,
start-up behaviour)."""

from qgis.core import QgsSettings
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .util import SETTINGS_GROUP, arcmap_icon, find_action, top_toolbars, tr

TB_ROLE = Qt.ItemDataRole.UserRole + 31


class CustomizeDialog(QDialog):
    def __init__(self, iface, actions):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.win = iface.mainWindow()
        self.custom = actions
        self.setObjectName("ArcMapCustomize")
        self.setWindowTitle(tr("Customize"))
        self.setWindowIcon(arcmap_icon("customize"))
        self.resize(620, 480)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs, 1)
        self.tabs.addTab(self._toolbars_tab(), tr("Toolbars"))
        self.tabs.addTab(self._commands_tab(), tr("Commands"))
        self.tabs.addTab(self._options_tab(), tr("Options"))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ----------------------------------------------------------- toolbars

    def _toolbars_tab(self):
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel(tr("Toolbars:"), page))
        self.tb_list = QListWidget(page)
        self._fill_toolbars()
        self.tb_list.itemChanged.connect(self._toolbar_toggled)
        layout.addWidget(self.tb_list, 1)
        row = QHBoxLayout()
        reset = QPushButton(tr("Reset ArcMap Layout"), page)
        reset.clicked.connect(lambda: (self.custom["reset_layout"].trigger() if "reset_layout" in self.custom else None, self._fill_toolbars()))
        row.addWidget(reset)
        row.addStretch(1)
        layout.addLayout(row)
        return page

    def _fill_toolbars(self):
        self.tb_list.blockSignals(True)
        self.tb_list.clear()
        for tb in sorted(top_toolbars(self.win), key=lambda t: (not t.objectName().startswith("ArcMap"), t.windowTitle().lower())):
            item = QListWidgetItem(tb.windowTitle())
            item.setData(TB_ROLE, tb.objectName())
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
            item.setCheckState(Qt.CheckState.Checked if tb.isVisible() else Qt.CheckState.Unchecked)
            self.tb_list.addItem(item)
        self.tb_list.blockSignals(False)

    def _toolbar(self, name):
        return next((t for t in top_toolbars(self.win) if t.objectName() == name), None)

    def _toolbar_toggled(self, item):
        tb = self._toolbar(item.data(TB_ROLE))
        if tb is not None:
            tb.setVisible(item.checkState() == Qt.CheckState.Checked)

    # ----------------------------------------------------------- commands

    def _commands_tab(self):
        page = QWidget(self)
        layout = QVBoxLayout(page)
        self.filter = QLineEdit(page)
        self.filter.setPlaceholderText(tr("Show commands containing:"))
        self.filter.textChanged.connect(self._fill_commands)
        layout.addWidget(self.filter)
        self.cmd_list = QListWidget(page)
        self.cmd_list.setIconSize(self.win.iconSize())
        layout.addWidget(self.cmd_list, 1)
        row = QHBoxLayout()
        self.add_button = QPushButton(tr("Add to Toolbar"), page)
        menu = QMenu(self.add_button)
        menu.aboutToShow.connect(lambda: self._fill_add_menu(menu))
        self.add_button.setMenu(menu)
        row.addWidget(self.add_button)
        run = QPushButton(tr("Run"), page)
        run.clicked.connect(self._run_selected)
        row.addWidget(run)
        row.addStretch(1)
        layout.addLayout(row)
        self._fill_commands("")
        return page

    def _all_actions(self):
        seen, out = set(), []
        for a in self.win.findChildren(QAction):
            text = a.text().replace("&", "").strip()
            if not text or a.isSeparator() or a.menu() is not None:
                continue
            key = (text, a.objectName())
            if key in seen:
                continue
            seen.add(key)
            out.append(a)
        return sorted(out, key=lambda a: a.text().replace("&", "").lower())

    def _fill_commands(self, text):
        text = text.lower()
        self.cmd_list.clear()
        for a in self._all_actions():
            label = a.text().replace("&", "")
            if text and text not in label.lower() and text not in a.objectName().lower():
                continue
            item = QListWidgetItem(a.icon(), label)
            item.setToolTip(a.objectName())
            item.setData(TB_ROLE, a)
            self.cmd_list.addItem(item)

    def _selected_action(self):
        item = self.cmd_list.currentItem()
        return item.data(TB_ROLE) if item else None

    def _fill_add_menu(self, menu):
        menu.clear()
        action = self._selected_action()
        for tb in sorted(top_toolbars(self.win), key=lambda t: t.windowTitle().lower()):
            entry = menu.addAction(tb.windowTitle())
            entry.setEnabled(action is not None)
            entry.triggered.connect(lambda _=False, t=tb, a=action: (t.addAction(a), t.setVisible(True)))

    def _run_selected(self):
        action = self._selected_action()
        if action is not None:
            action.trigger()

    # ------------------------------------------------------------ options

    def _options_tab(self):
        page = QWidget(self)
        layout = QVBoxLayout(page)
        settings = QgsSettings()
        self.start_cb = QCheckBox(tr("Apply the ArcMap look when QGIS starts"), page)
        self.start_cb.setChecked(settings.value(SETTINGS_GROUP + "/enabled", True, type=bool))
        self.start_cb.toggled.connect(lambda on: QgsSettings().setValue(SETTINGS_GROUP + "/enabled", on))
        layout.addWidget(self.start_cb)
        self.gs_cb = QCheckBox(tr("Show the Getting Started dialog at start-up"), page)
        self.gs_cb.setChecked(settings.value(SETTINGS_GROUP + "/show_getting_started", True, type=bool))
        self.gs_cb.toggled.connect(lambda on: QgsSettings().setValue(SETTINGS_GROUP + "/show_getting_started", on))
        layout.addWidget(self.gs_cb)
        self.large_cb = QCheckBox(tr("Large icons"), page)
        self.large_cb.setChecked(self.win.iconSize().width() >= 24)
        self.large_cb.toggled.connect(self._large_icons)
        layout.addWidget(self.large_cb)
        layout.addSpacing(12)
        for text, name in ((tr("Keyboard…"), "mActionConfigureShortcuts"),
                           (tr("Interface Customization…"), "mActionCustomization"),
                           (tr("ArcMap Options…"), "mActionOptions")):
            b = QPushButton(text, page)
            b.clicked.connect(lambda _=False, n=name: self._trigger(n))
            layout.addWidget(b)
        layout.addStretch(1)
        return page

    def _large_icons(self, on):
        from qgis.PyQt.QtCore import QSize

        size = QSize(24, 24) if on else QSize(18, 18)
        self.win.setIconSize(size)
        for tb in top_toolbars(self.win):
            tb.setIconSize(size)

    def _trigger(self, name):
        a = find_action(self.win, name)
        if a is not None:
            a.trigger()


def open_customize(iface, actions):
    dlg = CustomizeDialog(iface, actions)
    dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dlg.show()
    return dlg
