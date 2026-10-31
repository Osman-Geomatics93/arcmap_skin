# -*- coding: utf-8 -*-
"""Plugin object: the on/off switch and the ordered list of skin steps.

Switching the look on runs weighted steps in order (style sheet, icon
theme, window, menus, toolbars, panes, map frame, symbology, dialogs). Each
step records its undo in a shared :class:`util.Changes`. If any step fails,
everything is undone again: half a skin is worse than none. Switching off
replays the log and restores the window state saved before the first
switch-on, which lives in QgsSettings so it survives a restart.
"""

import traceback

from qgis.core import Qgis, QgsApplication, QgsMessageLog, QgsSettings
from qgis.PyQt.QtCore import QByteArray, QSize, QTimer
from qgis.PyQt.QtGui import QAction
from qgis.PyQt.QtWidgets import QMessageBox, QWidget

from . import (
    arctoolbox,
    attributes_window,
    canvas_menu,
    dialogs,
    edit_tool,
    editing,
    label_manager,
    layout_designer,
    settings as skin_settings,
    getting_started,
    shortcuts,
    toc_menu,
    icon_theme,
    mapview,
    menus,
    panes,
    stylesheet,
    symbology,
    toolbars,
)
from .actions import custom_actions
from .progress import ProgressBox, weighted
from .util import SETTINGS_GROUP, Changes, alive, top_toolbars, tr, ui_icon

KEY_ENABLED = SETTINGS_GROUP + "/enabled"
KEY_ORIGINAL_STATE = SETTINGS_GROUP + "/original_state"
KEY_ORIGINAL_GEOMETRY = SETTINGS_GROUP + "/original_geometry"
KEY_SKIN_STATE = SETTINGS_GROUP + "/skin_state"
KEY_LAYOUT_DONE = SETTINGS_GROUP + "/layout_done"
KEY_LAYOUT_VERSION = SETTINGS_GROUP + "/layout_version"
LAYOUT_VERSION = 2  # bump when the default ArcMap arrangement changes


def log(msg, level=None):
    QgsMessageLog.logMessage(str(msg), "ArcMap Skin", level or Qgis.MessageLevel.Info)


class ArcMapSkinPlugin:
    def __init__(self, iface, translator=None):
        self.iface = iface
        self.translator = translator
        self.win = iface.mainWindow()
        self.changes = Changes()
        self.actions = {}
        self.action = None
        self.on = False
        self._startup = False
        self._busy = False  # re-entrancy guard: enable() processes events
        self._unload_pending = False
        self._sheet = None

    # ------------------------------------------------------------ lifecycle

    def initGui(self):  # noqa: N802
        self.action = QAction(ui_icon("icon"), tr("ArcMap look"), self.win)
        self.action.setObjectName("ArcMapSkinToggle")
        self.action.setCheckable(True)
        self.action.setToolTip(tr("Switch the ArcMap look on or off"))
        self.action.triggered.connect(self.toggle)
        self.iface.addPluginToMenu(tr("&ArcMap Skin"), self.action)
        # "ArcMap Skin" page in QGIS Options with the feature switches
        self.options_factory = skin_settings.SettingsFactory(self)
        self.iface.registerOptionsWidgetFactory(self.options_factory)

        if QgsSettings().value(KEY_ENABLED, True, type=bool):
            if self.win.isVisible():
                QTimer.singleShot(0, self._enable_quietly)
            else:
                # QGIS is still starting: wait until the main window is up.
                # initializationCompleted may already have fired before the
                # plugins were restored, so poll for the window as well.
                self.iface.initializationCompleted.connect(self._enable_quietly)
                self._startup_timer = QTimer(self.win)
                self._startup_timer.setInterval(250)
                self._startup_timer.timeout.connect(self._poll_startup)
                self._startup_polls = 0
                self._startup_timer.start()
                log("Waiting for the main window before applying the look")

    def unload(self):
        try:
            self.iface.initializationCompleted.disconnect(self._enable_quietly)
        except (TypeError, RuntimeError):
            pass
        timer = getattr(self, "_startup_timer", None)
        if timer is not None and alive(timer):
            timer.stop()
        if self._busy:
            # Unloaded (e.g. reinstalled from ZIP) while the look is still
            # being applied: let enable() finish, then take it all back.
            self._unload_pending = True
            return
        if self.on:
            canvas = self.iface.mapCanvas()
            shutting_down = (not alive(canvas)) or canvas.isFrozen()
            if shutting_down:
                # Keep the look marked as on for the next start; just remember
                # where the user left the toolbars and panes.
                self._save_skin_state()
            else:
                self.disable(remember=False)
        if self.action is not None:
            self.iface.removePluginMenu(tr("&ArcMap Skin"), self.action)
            self.action.deleteLater()
            self.action = None
        factory = getattr(self, "options_factory", None)
        if factory is not None:
            self.iface.unregisterOptionsWidgetFactory(factory)
            self.options_factory = None

    def reapply(self):
        """Switch the look off and on again (after settings changed)."""
        if not self.on or self._busy:
            return
        try:
            self.disable(remember=False)
            self.enable()
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            log("Could not re-apply: %s" % exc, Qgis.MessageLevel.Warning)

    # -------------------------------------------------------------- toggle

    def toggle(self, checked):
        try:
            if checked:
                self.enable()
            else:
                self.disable()
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            QMessageBox.warning(
                self.win,
                tr("ArcMap Skin"),
                tr("The ArcMap look could not be switched. See the message log.\n\n%s") % exc,
            )

    def _poll_startup(self):
        self._startup_polls += 1
        if self.on or self._busy or self._startup_polls > 240 or not alive(self.win):  # give up after a minute
            self._startup_timer.stop()
            return
        if self.win.isVisible():
            self._startup_timer.stop()
            # One more turn of the loop so QGIS finishes restoring its state.
            QTimer.singleShot(0, self._enable_quietly)

    def _enable_quietly(self):
        if self.on or self._busy:
            return
        timer = getattr(self, "_startup_timer", None)
        if timer is not None and alive(timer):
            timer.stop()
        self._startup = True
        try:
            self.enable()
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            log("Could not enable: %s" % exc, Qgis.MessageLevel.Warning)

    # -------------------------------------------------------------- enable

    def _steps(self):
        """(name, weight, callback, feature key) – steps whose feature is
        switched off in the ArcMap Skin options page are skipped."""
        iface, changes = self.iface, self.changes
        on = skin_settings.enabled
        steps = [
            (tr("Style sheet"), 1, self._apply_stylesheet, None),
            (tr("Icons"), 4, lambda: icon_theme.apply_icon_theme(iface, changes), "icon_theme"),
            (tr("Window"), 1, self._apply_window, None),
            (tr("Commands"), 1, self._apply_actions, None),
            (tr("ArcToolbox"), 1, lambda: arctoolbox.install_arctoolbox(iface, changes, self.actions), "arctoolbox"),
            (tr("Editing"), 1, lambda: editing.install_editing(iface, changes, self.actions), "editing"),
            (tr("Edit tool"), 1, lambda: edit_tool.install_edit_tool(iface, changes, self.actions), "editing"),
            (tr("Attributes"), 1, lambda: attributes_window.install_attributes_window(iface, changes, self.actions), "editing"),
            (tr("Labeling"), 1, lambda: label_manager.install_label_manager(iface, changes, self.actions), "label_manager"),
            (tr("Menus"), 1, lambda: menus.build_menus(
                iface, changes, self.actions, lambda parent: toolbars.toolbars_menu(self.win, parent)), "menus"),
            (tr("Toolbars"), 2, lambda: toolbars.build_toolbars(iface, changes, self.actions), "toolbars"),
            (tr("Panes"), 2, lambda: panes.arrange_panes(iface, changes, self.actions), "panes"),
            (tr("Table Of Contents menu"), 1, lambda: toc_menu.install_toc_menu(iface, changes, self.actions), "toc_menu"),
            (tr("Shortcuts"), 1, lambda: shortcuts.apply_shortcuts(iface, changes), "shortcuts"),
            (tr("Map menu"), 1, lambda: canvas_menu.install_canvas_menu(iface, changes, self.actions), "canvas_menu"),
            (tr("Map frame"), 1, lambda: mapview.frame_map(iface, changes, self.actions), "map_frame"),
            (tr("Symbology"), 1, lambda: symbology.apply_symbology(iface, changes), "symbology"),
            (tr("Dialogs"), 1, lambda: dialogs.dress_windows(iface, changes), "dialogs"),
            (tr("Layout View"), 1, lambda: layout_designer.install_layout_designer(iface, changes), "layout_designer"),
            (tr("Layout"), 1, self._apply_layout, None),
        ]
        return [(name, weight, callback) for name, weight, callback, key in steps if key is None or on(key)]

    def _apply_actions(self):
        self.actions = custom_actions(self.iface, self.changes)
        editing.editor_actions(self.iface, self.changes, self.actions)
        if self.action is not None:
            self.actions["arcmap_look"] = self.action

    def enable(self):
        # The progress box processes events while the steps run, so a second
        # start-up trigger (signal + timer) could re-enter here and build
        # every toolbar, menu and pane twice. Guard against that.
        if self.on or self._busy:
            return
        self._busy = True
        timer = getattr(self, "_startup_timer", None)
        if timer is not None and alive(timer):
            timer.stop()
        try:
            self._remove_stale_widgets()
            settings = QgsSettings()
            if settings.value(KEY_ORIGINAL_STATE) is None:
                settings.setValue(KEY_ORIGINAL_STATE, self.win.saveState())
                settings.setValue(KEY_ORIGINAL_GEOMETRY, self.win.saveGeometry())
            box = ProgressBox(self.win, tr("Applying the ArcMap look…"))
            self.win.setUpdatesEnabled(False)
            try:
                import time

                timings = []
                for name, callback, base, span in weighted(self._steps()):
                    box.begin(name, base, span)
                    t0 = time.perf_counter()
                    callback()
                    timings.append("%s %.1fs" % (name, time.perf_counter() - t0))
                    box.fraction(1.0)
                log("Apply timings: " + ", ".join(timings))
            except Exception:
                self.win.setUpdatesEnabled(True)
                box.finish()
                try:
                    self.changes.undo()
                finally:
                    self._restore_original_window()
                    if self.action is not None:
                        self.action.setChecked(False)
                raise
            self.win.setUpdatesEnabled(True)
            box.finish()
            self.on = True
        finally:
            self._busy = False
        if getattr(self, "_unload_pending", False):
            self._unload_pending = False
            self.disable(remember=False)
            if self.action is not None:
                self.iface.removePluginMenu(tr("&ArcMap Skin"), self.action)
                self.action.deleteLater()
                self.action = None
            return
        settings.setValue(KEY_ENABLED, True)
        if self.action is not None:
            self.action.setChecked(True)
        log("ArcMap look on (%d changes recorded)" % len(self.changes))
        if self._startup:
            self._startup = False
            if skin_settings.enabled("getting_started"):
                QTimer.singleShot(800, lambda: getting_started.maybe_show(self.iface) if self.on else None)

    def _remove_stale_widgets(self):
        """Delete ArcMap toolbars, menus and panes left over from an earlier
        enable that was never undone (e.g. a crash or a double start-up)."""
        from qgis.PyQt.QtWidgets import QDockWidget, QToolBar

        win = self.win
        stale = 0
        for tb in win.findChildren(QToolBar):
            if tb.parent() is win and tb.objectName().startswith("ArcMap"):
                tb.hide()
                win.removeToolBar(tb)
                tb.setParent(None)
                tb.deleteLater()
                stale += 1
        for dock in win.findChildren(QDockWidget):
            if dock.parent() is win and dock.objectName().startswith("ArcMap"):
                dock.hide()
                win.removeDockWidget(dock)
                dock.setParent(None)
                dock.deleteLater()
                stale += 1
        bar = win.menuBar()
        for act in list(bar.actions()):
            menu = act.menu()
            if menu is not None and menu.objectName().startswith("ArcMap") and menu.objectName() != "ArcMapSkin":
                bar.removeAction(act)
                menu.setParent(None)
                menu.deleteLater()
                stale += 1
        central = win.centralWidget()
        if central is not None:
            for name in ("ArcMapStatusBar", "ArcMapViewButtons"):
                for w in central.findChildren(QWidget, name):
                    w.hide()
                    w.setParent(None)
                    w.deleteLater()
                    stale += 1
        if stale:
            log("Removed %d stale ArcMap widgets before applying the look" % stale, Qgis.MessageLevel.Warning)

    def _apply_stylesheet(self):
        block = stylesheet.load_qss(skin_settings.theme())
        self._sheet = stylesheet.StyleSheetBlock(self.win, block)

        def undo(sheet=self._sheet):
            sheet.remove()

        self.changes.add(undo)

    def _apply_window(self):
        win = self.win
        self.changes.set(win, "windowTitle", tr("Untitled - ArcMap Skin"))
        self.changes.set(win, "documentMode", True)
        # Compact ArcMap-size toolbar icons.
        self.changes.set(win, "iconSize", QSize(18, 18))

    def _apply_layout(self):
        """Place toolbars and panes: saved skin layout, or ArcMap defaults."""
        settings = QgsSettings()
        state = settings.value(KEY_SKIN_STATE)
        restored = False
        fresh_layout = settings.value(KEY_LAYOUT_VERSION, 0, type=int) != LAYOUT_VERSION
        if not fresh_layout and isinstance(state, QByteArray) and not state.isEmpty():
            restored = self.win.restoreState(state)
        if not restored or not any(tb.isVisible() for tb in top_toolbars(self.win)):
            toolbars.reset_toolbars(self.win)
            panes.reset_panes(self.win, close_others=fresh_layout)
            settings.setValue(KEY_LAYOUT_VERSION, LAYOUT_VERSION)
            settings.remove(KEY_SKIN_STATE)
        panes.ensure_native_toolbars_hidden(self.win)

    # ------------------------------------------------------------- disable

    def _save_skin_state(self):
        if alive(self.win):
            QgsSettings().setValue(KEY_SKIN_STATE, self.win.saveState())

    def _restore_original_window(self):
        settings = QgsSettings()
        state = settings.value(KEY_ORIGINAL_STATE)
        if isinstance(state, QByteArray) and not state.isEmpty() and alive(self.win):
            self.win.restoreState(state)
            if not any(tb.isVisible() for tb in top_toolbars(self.win)):
                _show_default_qgis_toolbars(self.win)
        settings.remove(KEY_ORIGINAL_STATE)
        settings.remove(KEY_ORIGINAL_GEOMETRY)

    def disable(self, remember=True):
        if not self.on:
            return
        self._save_skin_state()
        box = ProgressBox(self.win, tr("Restoring the QGIS look…"))
        self.win.setUpdatesEnabled(False)
        try:
            self.changes.undo(box.fraction)
        finally:
            self._restore_original_window()
            self.win.setUpdatesEnabled(True)
            box.finish()
            self.on = False
            self._sheet = None
            QgsApplication.instance().processEvents()
        if remember:
            QgsSettings().setValue(KEY_ENABLED, False)
        if self.action is not None:
            self.action.setChecked(False)
        log("ArcMap look off")


def _show_default_qgis_toolbars(win):
    for name in (
        "mFileToolBar",
        "mLayerToolBar",
        "mDigitizeToolBar",
        "mMapNavToolBar",
        "mAttributesToolBar",
        "mSelectionToolBar",
        "mLabelToolBar",
        "mPluginToolBar",
        "mDataSourceManagerToolBar",
        "mSnappingToolBar",
    ):
        tb = next((t for t in top_toolbars(win) if t.objectName() == name), None)
        if tb is not None:
            tb.setVisible(True)
