# -*- coding: utf-8 -*-
"""The ArcMap icon theme.

``resources/qgis_theme`` (built by ``scripts/build_icon_theme.py``) holds a
complete QGIS icon theme: every default QGIS icon redrawn in the ArcMap
palette, plus the hand-drawn ArcMap icons copied over the QGIS names they
replace. On switch-on the folder is installed as a QGIS theme named
``ArcMap`` and made the active theme. Icons already on screen are swapped
right away; QGIS caches theme icons by name, so icons in dialogs that were
already opened change after a restart.

If the theme has not been built, only the live swap of hand-drawn icons
happens, so the plugin works from a plain checkout too.
"""

import os
import shutil
from concurrent.futures import ThreadPoolExecutor

from qgis.core import Qgis, QgsApplication, QgsMessageLog, QgsSettings
from qgis.PyQt.QtCore import QDir, QDirIterator, QFile, QIODevice
from qgis.PyQt.QtGui import QPixmapCache
from qgis.PyQt.QtWidgets import QAbstractButton, QApplication, QWidget

from .util import RESOURCES, SETTINGS_GROUP, alive, arcmap_icon, has_icon, tr

THEME = "ArcMap"
THEME_SRC = os.path.join(RESOURCES, "qgis_theme")
MARKER = "arcmap_skin.version"
KEY_ORIGINAL_THEME = SETTINGS_GROUP + "/original_ui_theme"
NOTICE_PROPERTY = "arcmapRestartNotice"

# hand-drawn icon → QGIS theme icon names it replaces (without .svg)
ARCMAP_AS_QGIS = {
    "new_map": ["mActionFileNew"],
    "open": ["mActionFileOpen"],
    "save": ["mActionFileSave"],
    "save_as": ["mActionFileSaveAs"],
    "print": ["mActionNewLayout", "mActionFilePrint"],
    "cut": ["mActionEditCut"],
    "copy": ["mActionEditCopy"],
    "paste": ["mActionEditPaste"],
    "delete": ["mActionDeleteSelected", "mActionDeleteSelectedFeatures"],
    "undo": ["mActionUndo"],
    "redo": ["mActionRedo"],
    "add_data": ["mActionDataSourceManager", "mActionAddLayer"],
    "add_vector": ["mActionAddOgrLayer"],
    "add_raster": ["mActionAddRasterLayer"],
    "zoom_in": ["mActionZoomIn"],
    "zoom_out": ["mActionZoomOut"],
    "pan": ["mActionPan"],
    "full_extent": ["mActionZoomFullExtent"],
    "zoom_layer": ["mActionZoomToLayer", "mActionZoomToLayers"],
    "zoom_selected": ["mActionZoomToSelected"],
    "pan_selected": ["mActionPanToSelected"],
    "prev_extent": ["mActionZoomLast"],
    "next_extent": ["mActionZoomNext"],
    "select_rect": ["mActionSelectRectangle", "mActionSelect"],
    "select_polygon": ["mActionSelectPolygon"],
    "select_lasso": ["mActionSelectFreehand"],
    "select_circle": ["mActionSelectRadius"],
    "clear_selected": ["mActionDeselectAll", "mActionDeselectActiveLayer"],
    "switch_selection": ["mActionInvertSelection"],
    "select_all": ["mActionSelectAll"],
    "select_by_attributes": ["mIconExpressionSelect", "mActionSelectByExpression"],
    "identify": ["mActionIdentify"],
    "html_popup": ["mActionMapTips"],
    "measure": ["mActionMeasure"],
    "measure_area": ["mActionMeasureArea"],
    "bookmarks": ["mActionShowBookmarks"],
    "bookmark_new": ["mActionNewBookmark"],
    "refresh": ["mActionRefresh", "mActionDraw"],
    "viewer": ["mActionNewMap"],
    "time_slider": ["temporal_navigation", "mActionTemporalController"],
    "editor": ["mActionToggleEditing"],
    "save_edits": ["mActionSaveEdits", "mActionSaveAllEdits"],
    "sketch": ["mActionCapturePoint", "mActionCaptureLine", "mActionCapturePolygon"],
    "edit_vertices": ["mActionVertexTool", "mActionVertexToolActiveLayer"],
    "edit_tool": ["mActionMoveFeature", "mActionMoveFeatureLine", "mActionMoveFeaturePoint"],
    "reshape": ["mActionReshape"],
    "cut_polygons": ["mActionSplitFeatures"],
    "split": ["mActionSplitParts"],
    "rotate": ["mActionRotateFeature"],
    "attributes": ["mActionMultiEdit"],
    "table": ["mActionOpenTable", "mActionOpenTableSelected", "mActionOpenTableVisible", "mActionOpenTableEdited"],
    "field_calculator": ["mActionCalculateField"],
    "labeling": ["labelingSingle", "mActionLabeling"],
    "python": ["mActionShowPythonDialog", "mIconPythonFile"],
    "model_builder": ["processingModel"],
    "arctoolbox": ["processingAlgorithm"],
    "results": ["processingResult"],
    "history": ["mActionHistory"],
    "catalog": ["mActionFolder", "mIconFolder"],
    "toc": ["mActionLayoutManager", "mIconLayerTree"],
    "help": ["mActionHelpContents"],
    "options": ["mActionOptions"],
    "style_manager": ["mActionStyleManager"],
    "addins": ["mActionShowPluginManager"],
    "map_properties": ["mActionProjectProperties"],
    "layout_view": ["mActionNewLayout", "mIconLayout"],
    "north_arrow": ["north_arrow"],
    "scale_bar": ["mActionScaleBar"],
    "title": ["title_label"],
    "grid": ["transformed", "mActionAddGrid"],
    "crs": ["mIconProjectionEnabled", "mIconProjectionDisabled"],
    "georeferencing": ["mGeorefRun", "mActionShowGeoreferencer"],
    "raster_calculator": ["mActionShowRasterCalculator"],
    "statistics": ["mActionCalculateField", "statistics"],
    "search": ["search"],
    "folder": ["mIconFolder", "mIconFolderOpen"],
}


def log(msg, level=None):
    QgsMessageLog.logMessage(str(msg), "ArcMap Skin", level or Qgis.MessageLevel.Info)


def theme_built():
    return os.path.isdir(os.path.join(THEME_SRC, "icons")) and any(
        f.endswith(".svg") for f in os.listdir(os.path.join(THEME_SRC, "icons"))
    )


def _version():
    from .util import PLUGIN_DIR

    try:
        with open(os.path.join(PLUGIN_DIR, "metadata.txt"), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("version="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "dev"


def _writable(folder):
    """os.access() lies on Windows ACLs: actually try to create a file."""
    if not folder or not os.path.isdir(folder):
        return False
    probe = os.path.join(folder, ".arcmap_skin_probe")
    try:
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("x")
        os.remove(probe)
        return True
    except OSError:
        return False


def _themes_folder():
    """Writable themes folder: the user profile first (never touch the QGIS
    installation unless the profile folder cannot be written)."""
    user = QgsApplication.userThemesFolder()
    try:
        os.makedirs(user, exist_ok=True)
    except OSError:
        pass
    if _writable(user):
        return user
    default = QgsApplication.defaultThemesFolder()
    if _writable(default):
        return default
    return user


def _marker(folder):
    try:
        with open(os.path.join(folder, MARKER), encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _mark(folder, text):
    try:
        with open(os.path.join(folder, MARKER), "w", encoding="utf-8") as fh:
            fh.write(text)
    except OSError:
        pass


def _copy_tree(src, dst):
    files = []
    for root, _dirs, names in os.walk(src):
        rel = os.path.relpath(root, src)
        target = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(target, exist_ok=True)
        for n in names:
            files.append((os.path.join(root, n), os.path.join(target, n)))

    def copy(pair):
        try:
            shutil.copyfile(*pair)
        except OSError as exc:
            log("Could not write %s: %s" % (pair[1], exc), Qgis.MessageLevel.Warning)

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(copy, files))
    return len(files)


def install_icon_theme():
    """Copy the built theme into the themes folder. Returns its path or None."""
    if not theme_built():
        return None
    folder = os.path.join(_themes_folder(), THEME)
    stamp = "arcmap " + _version()
    if _marker(folder) == stamp:
        return folder
    os.makedirs(folder, exist_ok=True)
    count = _copy_tree(THEME_SRC, folder)
    # QGIS expects style.qss/variables.qss next to icons/.
    for name in ("style.qss", "variables.qss"):
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("/* ArcMap Skin icon theme: styling comes from the plugin */\n" if name == "style.qss" else "")
    _mark(folder, stamp)
    log("Installed icon theme (%d files) to %s" % (count, folder))
    return folder


def _write_qgis_icons(folder):
    """Overwrite the theme's SVGs with QGIS's own, so cached file icons revert."""
    icons = os.path.join(folder, "icons")
    it = QDirIterator(":/images/themes/default", ["*.svg"], QDir.Filter.Files, QDirIterator.IteratorFlag.Subdirectories)
    pairs = []
    while it.hasNext():
        src = it.next()
        rel = src[len(":/images/themes/default/"):]
        dst = os.path.join(icons, rel)
        if os.path.exists(dst):
            pairs.append((src, dst))

    def write(pair):
        src, dst = pair
        f = QFile(src)
        if f.open(QIODevice.OpenModeFlag.ReadOnly):
            data = bytes(f.readAll())
            f.close()
            try:
                with open(dst, "wb") as out:
                    out.write(data)
            except OSError:
                pass

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, pairs))
    _mark(folder, "qgis")


# ------------------------------------------------------------ live swapping


def _icon_map():
    """QGIS theme-icon cacheKey → hand-drawn QIcon, for icons on screen now."""
    mapping = {}
    for key, names in ARCMAP_AS_QGIS.items():
        if not has_icon(key):
            continue
        icon = arcmap_icon(key)
        for name in names:
            for candidate in (name + ".svg", name + ".png"):
                qicon = QgsApplication.getThemeIcon("/" + candidate)
                if not qicon.isNull():
                    mapping[qicon.cacheKey()] = icon
    return mapping


def holders_in(widgets, win=None):
    """Actions and buttons that carry an icon in the given widgets."""
    seen = set()
    holders = []
    for w in widgets:
        if not alive(w):
            continue
        for action in w.actions():
            if id(action) not in seen:
                seen.add(id(action))
                holders.append(action)
        if isinstance(w, QAbstractButton):
            holders.append(w)
    if win is not None:
        from qgis.PyQt.QtGui import QAction

        for action in win.findChildren(QAction):
            if id(action) not in seen:
                seen.add(id(action))
                holders.append(action)
    return holders


def swap_icons(holders, mapping, changes=None):
    count = 0
    for holder in holders:
        try:
            current = holder.icon()
        except (RuntimeError, AttributeError):
            continue
        if current.isNull():
            continue
        new = mapping.get(current.cacheKey())
        if new is None:
            continue
        if changes is not None:
            changes.set(holder, "icon", new)
        else:
            holder.setIcon(new)
        count += 1
    return count


def _redraw():
    QPixmapCache.clear()
    for w in QApplication.allWidgets():
        if alive(w):
            w.update()


def _restart_notice(iface):
    app = QApplication.instance()
    if app.property(NOTICE_PROPERTY):
        return
    app.setProperty(NOTICE_PROPERTY, True)
    iface.messageBar().pushMessage(
        tr("ArcMap Skin"),
        tr("Layer and dialog icons finish changing after QGIS is restarted."),
        Qgis.MessageLevel.Info,
        8,
    )


def apply_icon_theme(iface, changes):
    win = iface.mainWindow()
    settings = QgsSettings()
    started_with_theme = QgsApplication.themeName() == THEME
    folder = install_icon_theme()
    if folder is not None:
        if settings.value(KEY_ORIGINAL_THEME) is None:
            previous = QgsApplication.themeName() or "default"
            settings.setValue(KEY_ORIGINAL_THEME, "default" if previous == THEME else previous)
        QgsApplication.setThemeName(THEME)
        settings.setValue("UI/UITheme", THEME)

    mapping = _icon_map()
    widgets = [w for w in win.findChildren(QWidget) if w.isVisible()]
    swapped = swap_icons(holders_in(widgets, win), mapping, changes)
    log("Swapped %d live icons" % swapped)

    def undo(folder=folder, started_with_theme=started_with_theme, iface=iface):
        settings = QgsSettings()
        original = settings.value(KEY_ORIGINAL_THEME, "default")
        if folder is not None:
            QgsApplication.setThemeName(original if original != THEME else "default")
            if original and original != "default":
                settings.setValue("UI/UITheme", original)
            else:
                settings.remove("UI/UITheme")
            settings.remove(KEY_ORIGINAL_THEME)
            if started_with_theme:
                # Icons cached from the theme files cannot be evicted; make
                # the files QGIS's own until the next switch-on rewrites them.
                _write_qgis_icons(folder)
        _redraw()

    changes.add(undo)
    if folder is not None and not started_with_theme:
        _restart_notice(iface)
    _redraw()
