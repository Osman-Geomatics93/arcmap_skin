# -*- coding: utf-8 -*-
"""ArcMap's right-click menu on the map (Select Elements tool): Zoom In /
Out, Full Extent, Previous / Next Extent, Go To XY, Add Data, Pause
Drawing, Data Frame Properties. Added to QGIS's own canvas context menu."""

from qgis.PyQt.QtCore import QObject

from .util import alive, arcmap_icon, find_action, tr


class CanvasMenu(QObject):
    def __init__(self, iface, actions):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.win = iface.mainWindow()
        self.canvas = iface.mapCanvas()
        self.custom = actions
        self.canvas.contextMenuAboutToShow.connect(self.extend)

    def extend(self, menu, event):
        qgis_actions = list(menu.actions())
        first = qgis_actions[0] if qgis_actions else None
        canvas = self.canvas

        def insert(action):
            if action is None:
                return
            if first is not None:
                menu.insertAction(first, action)
            else:
                menu.addAction(action)

        def new(text, icon, callback):
            from qgis.PyQt.QtGui import QAction

            a = QAction(arcmap_icon(icon), text, menu)
            a.triggered.connect(callback)
            insert(a)
            return a

        new(tr("Zoom In"), "fixed_zoom_in", lambda: canvas.zoomIn())
        new(tr("Zoom Out"), "fixed_zoom_out", lambda: canvas.zoomOut())
        insert(find_action(self.win, "mActionZoomFullExtent"))
        insert(find_action(self.win, "mActionZoomLast"))
        insert(find_action(self.win, "mActionZoomNext"))
        if first is not None:
            menu.insertSeparator(first)
        else:
            menu.addSeparator()
        insert(self.custom.get("go_to_xy"))
        insert(self.custom.get("add_data"))
        insert(self.custom.get("pause_drawing"))
        if first is not None:
            menu.insertSeparator(first)
        else:
            menu.addSeparator()
        props = find_action(self.win, "mActionProjectProperties")
        if props is not None:
            new(tr("Data Frame Properties…"), "map_properties", props.trigger)
        if qgis_actions and first is not None:
            menu.insertSeparator(first)

    def stop(self):
        if alive(self.canvas):
            try:
                self.canvas.contextMenuAboutToShow.disconnect(self.extend)
            except (TypeError, RuntimeError):
                pass


def install_canvas_menu(iface, changes, actions):
    menu = CanvasMenu(iface, actions)
    changes.add(menu.stop)
    return menu
