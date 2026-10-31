#!/usr/bin/env python3
"""Generate the hand-drawn ArcMap-style toolbar icons (original artwork).

    python scripts/draw_icons.py

Writes one 16×16 SVG per icon into arcmap_skin/resources/icons/arcmap/.
The drawings follow ArcMap 10's visual language (yellow Add Data diamond,
blue globe, pencil editor, cyan selection …) but are all drawn from
scratch here from simple primitives, flat and crisp at any DPI.
"""

import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "arcmap_skin", "resources", "icons", "arcmap")

# palette (flattened ArcMap colours)
Y, YD = "#F2B822", "#B08300"
B, BD, BL = "#3B78C4", "#2A5A99", "#BBD7F2"
G, GD, GL = "#3A9E3A", "#23702A", "#CFE3B4"
R, RD = "#D0352B", "#9A2018"
O, OD = "#F0A050", "#C0601A"
P = "#8A63C4"
C = "#00C8E0"  # selection cyan
K = "#3A3A3A"  # dark stroke
M = "#8A8A8A"  # mid grey
L = "#D9D9D9"  # light grey
W = "#FFFFFF"

HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">'
TAIL = "</svg>"


def s(d, stroke=K, w=1.2, fill="none", extra=""):
    return '<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"%s/>' % (
        d, fill, stroke, w, extra)


def f(d, fill, stroke="none", w=1, extra=""):
    return '<path d="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"%s/>' % (d, fill, stroke, w, extra)


def rect(x, y, w_, h, fill, stroke="none", sw=1, rx=0):
    return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/>' % (
        x, y, w_, h, rx, fill, stroke, sw)


def circ(cx, cy, r, fill, stroke="none", sw=1, dash=""):
    return '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="%s"%s/>' % (
        cx, cy, r, fill, stroke, sw, ' stroke-dasharray="%s"' % dash if dash else "")


def line(x1, y1, x2, y2, stroke=K, w=1.2, dash=""):
    return '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"%s/>' % (
        x1, y1, x2, y2, stroke, w, ' stroke-dasharray="%s"' % dash if dash else "")


def text(x, y, t, size=7, fill=K, weight="bold", family="Arial, Helvetica, sans-serif", anchor="middle"):
    return '<text x="%s" y="%s" font-family="%s" font-size="%s" font-weight="%s" fill="%s" text-anchor="%s">%s</text>' % (
        x, y, family, size, weight, fill, anchor, t)


# ---------------------------------------------------------------- parts

def magnifier(inner=""):
    return (circ(6.5, 6.5, 4.6, BL, K, 1.3) + inner + line(10, 10, 14.2, 14.2, K, 2.2))


def page(x=3, y=1.5, w_=10, h=13, fill=W):
    d = "M%s %sh%sl3 3v%sH%sz" % (x, y, w_ - 3, h - 3, x)
    fold = "M%s %sv3h3" % (x + w_ - 3, y)
    return f(d, fill, K, 1.1) + s(fold, K, 1)


def globe(cx=8, cy=8, r=6):
    return (circ(cx, cy, r, BL, BD, 1.2)
            + f("M%s %sc1.5-1 3-.5 3.6 1 .6 1.5-.4 2.6-1.4 3.4-1 .8-2.4.6-3-.6s-.4-2.8.8-3.8z" % (cx - 4.2, cy - 2.6), G)
            + f("M%s %sc1.2-.6 2.4-.2 2.8 1 .3 1-.3 2-1.2 2.5-.9.4-1.9.1-2.2-.8-.3-1 .1-2.2.6-2.7z" % (cx + .8, cy + .6), G))


def pencil(x=3, y=12, color=Y):
    # diagonal pencil from bottom-left (x,y) to top-right
    return (f("M%s %sl8-8 2 2-8 8-2.6.6z" % (x, y), color, K, 1)
            + f("M%s %sl-2.6.6.6-2.6z" % (x + 2, y + 2 - 2), K)
            + line(x + 6.8, y - 6.8, x + 8.8, y - 4.8, K, 1))


def arrow_cursor(x=3, y=2, fill=W):
    return f("M%s %sv10l2.6-2.2 1.8 3.8 1.8-.9-1.8-3.7 3.4-.3z" % (x, y), fill, K, 1.1)


def layer_stack():
    return (f("M8 3l6 3-6 3-6-3z", BL, BD, 1) + f("M2 8.5l6 3 6-3", "none", BD, 1.2)
            + f("M2 11l6 3 6-3", "none", BD, 1.2))


def table(x=1.5, y=2.5, w_=13, h=11, head=BL):
    out = rect(x, y, w_, h, W, K, 1.1) + rect(x, y, w_, 3, head)
    out += line(x, y + 6.3, x + w_, y + 6.3, M, .8) + line(x, y + 9.7, x + w_, y + 9.7, M, .8)
    out += line(x + 4.3, y, x + 4.3, y + h, M, .8) + line(x + 8.7, y, x + 8.7, y + h, M, .8)
    return out


def dashed_rect():
    return rect(2.5, 3.5, 9, 7, "none", K, 1.2) .replace('stroke-width="1.2"', 'stroke-width="1.2" stroke-dasharray="2 1.4"')


def record_arrow(direction, bar=False):
    out = ""
    if direction == "left":
        out += f("M11 3l-6 5 6 5z", K)
        if bar:
            out += rect(3, 3, 1.8, 10, K)
    else:
        out += f("M5 3l6 5-6 5z", K)
        if bar:
            out += rect(11.2, 3, 1.8, 10, K)
    return out


def toolbox(color=R):
    return (rect(1.5, 6, 13, 8, color, RD, 1) + f("M5.5 6V4.5a2.5 2.5 0 0 1 5 0V6", "none", K, 1.3)
            + rect(1.5, 8.5, 13, 1.4, RD) + rect(6.5, 8, 3, 2.4, Y, YD, .8))


def polygon_overlay(a_fill, b_fill, inter_fill=None):
    out = circ(6, 8, 4.5, a_fill, K, 1) + circ(10, 8, 4.5, b_fill, K, 1)
    if inter_fill:
        out += f("M8 4.3a4.5 4.5 0 0 1 0 7.4 4.5 4.5 0 0 1 0-7.4z", inter_fill, K, 1)
    return out


# ------------------------------------------------------------------ icons

ICONS = {}


def icon(name):
    def deco(fn):
        ICONS[name] = fn
        return fn
    return deco


# -- files
@icon("new_map")
def _(): return page() + f("M11 9.5h3M12.5 8v3", "none", G, 1.6) if False else page() + s("M9.5 11h4M11.5 9v4", G, 1.6)


@icon("open")
def _(): return (f("M1.5 4h4l1.5 1.5h7.5V13h-13z", Y, YD, 1) + f("M1.5 13l2-6h12l-2 6z", "#F8D77A", YD, 1))


@icon("save")
def _(): return (f("M2 2h10l2 2v10H2z", B, BD, 1) + rect(4.5, 2, 6, 4, W) + rect(4, 9, 8, 5, "#DCE9F7") + rect(8.5, 2.8, 1.5, 2.4, BD))


@icon("save_as")
def _(): return ICONS["save"]() + pencil(8, 15, Y)


@icon("save_edits")
def _(): return ICONS["save"]() + pencil(8, 15, Y)


@icon("print")
def _(): return (rect(2, 6, 12, 6, M, K, 1, 1) + rect(4.5, 2, 7, 4, W, K, 1) + rect(4.5, 10, 7, 4.5, W, K, 1) + circ(12, 8, .8, G))


@icon("page_setup")
def _(): return page() + rect(5, 6, 6, 5, "none", B, 1.1)


@icon("export_map")
def _(): return page() + s("M6 12l4-4M10 8h-3M10 8v3", B, 1.5)


@icon("exit")
def _(): return (s("M9 2.5H3v11h6", K, 1.3) + s("M7 8h7M11.5 5.5L14 8l-2.5 2.5", R, 1.5))


@icon("map_properties")
def _(): return (page() + s("M5 6h6M5 8.5h6M5 11h4", M, 1))


@icon("properties")
def _(): return ICONS["map_properties"]()


@icon("report")
def _(): return page() + rect(5, 8, 1.6, 4, B) + rect(7.4, 6, 1.6, 6, G) + rect(9.8, 9.5, 1.6, 2.5, O)


# -- edit
@icon("cut")
def _(): return (circ(4.5, 12, 2.3, "none", K, 1.3) + circ(11.5, 12, 2.3, "none", K, 1.3)
                 + s("M6 10.3L12 2M10 10.3L4 2", K, 1.3))


@icon("copy")
def _(): return (rect(2, 2, 8, 9, W, K, 1.1) + rect(6, 5, 8, 9, W, K, 1.1) + s("M8 8h4M8 10h4", M, 1))


@icon("paste")
def _(): return (rect(2.5, 3, 9, 11, "#E8D3A6", OD, 1) + rect(5, 2, 4, 2.5, M, K, .8) + rect(7, 6, 7, 8, W, K, 1)
                 + s("M9 9h3M9 11h3", M, 1))


@icon("delete")
def _(): return s("M3.5 3.5l9 9M12.5 3.5l-9 9", R, 2.2)


@icon("undo")
def _(): return (s("M4 7h6.5a3 3 0 0 1 0 6H6", B, 1.8) + f("M4 7l3-3v6z", B))


@icon("redo")
def _(): return (s("M12 7H5.5a3 3 0 0 0 0 6H10", B, 1.8) + f("M12 7l-3-3v6z", B))


@icon("add_data")
def _(): return (f("M8 1.2l6.8 6.8L8 14.8 1.2 8z", Y, YD, 1) + s("M8 4.5v7M4.5 8h7", K, 1.8))


@icon("add_vector")
def _(): return (f("M2 4l5-2 7 3-5 2.5-7-1.5z", GL, GD, 1) + s("M11 10v4M9 12h4", G, 1.6))


@icon("add_raster")
def _(): return (rect(2, 2, 9, 9, L, K, 1) + rect(2, 2, 4.5, 4.5, BL) + rect(6.5, 6.5, 4.5, 4.5, GL)
                 + s("M12 10v4M10 12h4", G, 1.6))


@icon("new_layer")
def _(): return (f("M2 6l6-3 6 3-6 3z", GL, GD, 1) + s("M12 10v4M10 12h4", G, 1.6))


@icon("graphics_layer")
def _(): return (f("M2 6l6-3 6 3-6 3z", "#F6D9C8", OD, 1) + pencil(8, 15, Y))


# -- navigation
@icon("zoom_in")
def _(): return magnifier(s("M6.5 4.2v4.6M4.2 6.5h4.6", K, 1.5))


@icon("zoom_out")
def _(): return magnifier(s("M4.2 6.5h4.6", K, 1.5))


@icon("fixed_zoom_in")
def _(): return (magnifier(s("M6.5 4.2v4.6M4.2 6.5h4.6", K, 1.5))
                 + rect(1, 1, 14, 14, "none", M, .8).replace('stroke-width="0.8"', 'stroke-width="0.8" stroke-dasharray="1.5 1.2"'))


@icon("fixed_zoom_out")
def _(): return (magnifier(s("M4.2 6.5h4.6", K, 1.5))
                 + rect(1, 1, 14, 14, "none", M, .8).replace('stroke-width="0.8"', 'stroke-width="0.8" stroke-dasharray="1.5 1.2"'))


@icon("pan")
def _(): return (f("M5 14.5c-1.5-1.5-2.8-4-2.8-6 0-.9 1.2-1.1 1.6-.2l.9 1.9V4.2c0-1.2 1.6-1.2 1.6 0v3.5V3c0-1.2 1.7-1.2 1.7 0v4.5V3.8c0-1.2 1.6-1.2 1.6 0v4V5.5c0-1.2 1.6-1.2 1.6 0V11c0 2-1.4 3.5-3.2 3.5z",
                   "#F8E3C8", K, 1))


@icon("full_extent")
def _(): return globe()


@icon("zoom_layer")
def _(): return (f("M2 6l6-3 6 3-6 3z", GL, GD, 1) + magnifier(s("M6.5 4.2v4.6M4.2 6.5h4.6", K, 1.5)).replace('viewBox', 'x') if False else
                 magnifier() + f("M3.3 7.2l3.2-1.6 3.2 1.6-3.2 1.6z", G))


@icon("zoom_selected")
def _(): return magnifier(f("M4 7l2.5-1.3L9 7l-2.5 1.3z", C, K, .6))


@icon("pan_selected")
def _(): return (f("M4 7l2.5-1.3L9 7l-2.5 1.3z", C, K, .6) + s("M12 3v10M9.5 5.5L12 3l2.5 2.5M9.5 10.5L12 13l2.5-2.5", K, 1.3))


@icon("prev_extent")
def _(): return (s("M12 4H6a3 3 0 0 0 0 6h5", B, 1.8) + f("M12 4l-3-3v6z", B) + s("M3 13h10", M, 1))


@icon("next_extent")
def _(): return (s("M4 4h6a3 3 0 0 1 0 6H5", B, 1.8) + f("M4 4l3-3v6z", B) + s("M3 13h10", M, 1))


@icon("refresh")
def _(): return (s("M12.5 8a4.5 4.5 0 1 1-1.3-3.2", G, 1.8) + f("M13.5 2.5v4h-4z", G))


@icon("pause_drawing")
def _(): return rect(4, 3, 3, 10, K) + rect(9, 3, 3, 10, K)


@icon("viewer")
def _(): return (rect(1.5, 2.5, 13, 9, W, K, 1.1) + rect(1.5, 2.5, 13, 2.2, BL) + globe(8, 8.5, 2.6) + rect(5, 12.5, 6, 1.2, M))


@icon("overview")
def _(): return (rect(1.5, 2.5, 13, 11, BL, BD, 1) + rect(8, 7.5, 5, 4.5, "none", R, 1.3))


@icon("data_view")
def _(): return (rect(1.5, 2.5, 13, 11, W, K, 1) + globe(8, 8, 4.3))


@icon("layout_view")
def _(): return (rect(3, 1.5, 10, 13, W, K, 1) + rect(5, 3.5, 6, 5, BL, BD, .8) + rect(5, 10, 6, 1, M) + rect(5, 12, 4, 1, M))


# -- selection
@icon("select_features")
def _(): return dashed_rect() + arrow_cursor(7, 6, C)


@icon("select_rect")
def _(): return dashed_rect() + arrow_cursor(7, 6, C)


@icon("select_polygon")
def _(): return (s("M3 10L5 3l7 1 2 6-5 3z", K, 1.2).replace('stroke-linejoin="round"', 'stroke-linejoin="round" stroke-dasharray="2 1.4"')
                 + arrow_cursor(7, 6, C))


@icon("select_lasso")
def _(): return (s("M8 2.5c4 0 6 1.8 6 3.8s-2.5 3.7-6 3.7c-2 0-3.5-.6-4.3-1.3-1 1-1.4 2.5-1.2 4.3", K, 1.2).replace('stroke-linejoin="round"', 'stroke-linejoin="round" stroke-dasharray="2 1.4"')
                 + arrow_cursor(8, 6, C))


@icon("select_circle")
def _(): return circ(7, 7, 5, "none", K, 1.2, "2 1.4") + arrow_cursor(7, 6, C)


@icon("select_elements")
def _(): return arrow_cursor(4, 1.5, W)


@icon("select_all")
def _(): return (rect(2, 2, 12, 12, C, K, 1) + s("M4.5 8.5l2.5 2.5 4.5-5", W, 1.8))


@icon("clear_selected")
def _(): return (rect(2.5, 3.5, 8, 7, "none", K, 1.1, 0).replace('stroke-width="1.1"', 'stroke-width="1.1" stroke-dasharray="2 1.4"')
                 + s("M9 9l5 5M14 9l-5 5", R, 1.8))


@icon("switch_selection")
def _(): return (rect(2, 3, 5.5, 5, C, K, 1) + rect(8.5, 8, 5.5, 5, "none", K, 1, 0).replace('stroke-width="1"', 'stroke-width="1" stroke-dasharray="1.6 1.2"')
                 + s("M9 4.5h3.5L11 3M12.5 4.5L11 6M7 11.5H3.5L5 10M3.5 11.5L5 13", K, 1.1))


@icon("select_by_attributes")
def _(): return table(1.5, 2, 13, 10) + f("M5 7l6 .9-2.2 1.3 1.8 3.8-1.6.8-1.8-3.9-2.1 1.4z", C, K, .9)


@icon("select_by_location")
def _(): return (f("M2 11l5-2 7 1-5 3-7-1z", GL, GD, 1) + f("M8 1.5a3.5 3.5 0 0 1 3.5 3.5c0 2.6-3.5 6-3.5 6S4.5 7.6 4.5 5A3.5 3.5 0 0 1 8 1.5z", C, K, 1)
                 + circ(8, 5, 1.3, W))


@icon("statistics")
def _(): return (rect(2, 9, 2.5, 5, B) + rect(5.5, 5, 2.5, 9, G) + rect(9, 7, 2.5, 7, O) + rect(12.5, 3, 2, 11, R) + line(1.5, 14.5, 15, 14.5, K, 1))


# -- tools
@icon("identify")
def _(): return (circ(8, 8, 6.5, BL, BD, 1.2) + circ(8, 4.8, 1.1, BD) + rect(7, 7, 2, 5, BD))


@icon("html_popup")
def _(): return (f("M2 2.5h12v8H7l-3 3v-3H2z", W, K, 1.1) + text(8, 9, "i", 7.5, B, "bold", "Georgia, serif"))


@icon("measure")
def _(): return (f("M1.5 11.5L11.5 1.5l3 3-10 10z", Y, YD, 1) + s("M4 9l1.5 1.5M6 7l1 1M8 5l1.5 1.5M10 3l1 1", K, 1))


@icon("measure_area")
def _(): return ICONS["measure"]() + f("M9 10l4 1.5-1 3.5-4-1.5z", GL, GD, .8)


@icon("find")
def _(): return (circ(4.8, 10, 3.3, K) + circ(11.2, 10, 3.3, K) + circ(4.8, 10, 1.6, BL) + circ(11.2, 10, 1.6, BL)
                 + f("M4 3h2.5l1 4h-4.5zM9.5 3H12l1 4H8.5z", K) + rect(6.5, 5, 3, 1.5, K))


@icon("go_to_xy")
def _(): return (line(8, 1.5, 8, 14.5, M, 1) + line(1.5, 8, 14.5, 8, M, 1) + circ(8, 8, 2.2, "none", R, 1.5)
                 + text(12.5, 6.5, "X", 5.5, K) + text(5, 13.5, "Y", 5.5, K))


@icon("hyperlink")
def _(): return (s("M6.5 9.5a2.5 2.5 0 0 1 0-3.5l2-2a2.5 2.5 0 0 1 3.5 3.5l-.8.8", B, 1.6)
                 + s("M9.5 6.5a2.5 2.5 0 0 1 0 3.5l-2 2A2.5 2.5 0 0 1 4 8.5l.8-.8", B, 1.6))


@icon("time_slider")
def _(): return (circ(8, 8, 6.3, W, K, 1.2) + s("M8 4.2V8l2.6 1.8", K, 1.4) + circ(8, 8, .9, K))


@icon("crs")
def _(): return globe(8, 8, 6) + s("M8 2v12M2 8h12M3.8 4.5c2.5 1.5 5.9 1.5 8.4 0M3.8 11.5c2.5-1.5 5.9-1.5 8.4 0", "none", BD, .8).replace('fill="none"', 'fill="none"')


@icon("bookmarks")
def _(): return f("M4 1.5h8v13l-4-3-4 3z", B, BD, 1)


@icon("bookmark_new")
def _(): return f("M3 1.5h7v12l-3.5-2.6L3 13.5z", B, BD, 1) + s("M12.5 3v5M10 5.5h5", G, 1.6)


# -- editor
@icon("editor")
def _(): return pencil(2.5, 13.5, Y)


@icon("edit_tool")
def _(): return arrow_cursor(2, 1.5, W) + pencil(7, 15, Y)


@icon("sketch")
def _(): return (s("M2.5 12.5L7 5l4 5 3-7", K, 1.3) + circ(2.5, 12.5, 1.4, G, K, .8) + circ(7, 5, 1.4, G, K, .8)
                 + circ(11, 10, 1.4, G, K, .8) + circ(14, 3, 1.4, R, K, .8))


@icon("edit_vertices")
def _(): return (s("M2.5 12.5L7 5l4 5 3-7", K, 1.2) + rect(1.3, 11.3, 2.4, 2.4, W, K, .9) + rect(5.8, 3.8, 2.4, 2.4, G, K, .9)
                 + rect(9.8, 8.8, 2.4, 2.4, W, K, .9) + rect(12.8, 1.8, 2.4, 2.4, W, K, .9))


@icon("reshape")
def _(): return (f("M2 4h8v8H2z", GL, GD, 1) + s("M10 6c3 0 4 2 4 4s-1 4-4 4", R, 1.5).replace('stroke-linejoin="round"', 'stroke-linejoin="round" stroke-dasharray="2 1.3"'))


@icon("cut_polygons")
def _(): return (f("M2 3h12v10H2z", GL, GD, 1) + s("M5 1.5l6 13", R, 1.6).replace('stroke-linejoin="round"', 'stroke-linejoin="round" stroke-dasharray="2.2 1.4"'))


@icon("split")
def _(): return (s("M2 8h5M9 8h5", K, 1.6) + s("M8 2v12", R, 1.4).replace('stroke-linejoin="round"', 'stroke-linejoin="round" stroke-dasharray="2 1.3"'))


@icon("rotate")
def _(): return (f("M4 6h7v7H4z", GL, GD, 1) + s("M13.5 5A5.5 5.5 0 0 0 4 3.5", B, 1.6) + f("M4 1v4h4z", B))


@icon("attributes")
def _(): return table(1.5, 2, 13, 11)


@icon("sketch_properties")
def _(): return (table(1.5, 2, 13, 11) + circ(12, 12, 3.2, G, GD, .8) + s("M10.5 12h3M12 10.5v3", W, 1.2))


@icon("create_features")
def _(): return (f("M2 5l5-2 7 3-5 2.5-7-1.5z", GL, GD, 1) + s("M12 9.5v5M9.5 12h5", G, 1.8))


@icon("add_record")
def _(): return table(1.5, 2, 10, 9) + s("M12 9.5v5M9.5 12h5", G, 1.8)


@icon("add_field")
def _(): return table(1.5, 2, 10, 9) + rect(12, 2, 2.5, 9, Y, YD, .8) + s("M13.2 4v5M11.5 6.5h3.5", K, 1)


@icon("field_calculator")
def _(): return (rect(2.5, 1.5, 11, 13, L, K, 1, 1) + rect(4.5, 3, 7, 3, W, K, .8) + rect(4.5, 7.5, 2, 2, K)
                 + rect(7, 7.5, 2, 2, K) + rect(9.5, 7.5, 2, 2, K) + rect(4.5, 10.5, 2, 2, K) + rect(7, 10.5, 2, 2, K) + rect(9.5, 10.5, 2, 2, O))


@icon("table")
def _(): return table()


@icon("table_options")
def _(): return table(1.5, 2, 13, 11) + f("M9 15l3-4h-6z", K)


@icon("selected_to_top")
def _(): return table(1.5, 3, 10, 10, C) + s("M13.5 12V5M11.5 7l2-2 2 2", K, 1.3)


@icon("show_all_records")
def _(): return table(1.5, 2, 13, 12)


@icon("show_selected_records")
def _(): return table(1.5, 2, 13, 12) + rect(1.5, 5.6, 13, 3.3, C)


@icon("first_record")
def _(): return record_arrow("left", True)


@icon("prev_record")
def _(): return record_arrow("left")


@icon("next_record")
def _(): return record_arrow("right")


@icon("last_record")
def _(): return record_arrow("right", True)


# -- panes & windows
@icon("toc")
def _(): return layer_stack()


@icon("list_by_drawing_order")
def _(): return (rect(2, 2.5, 3, 3, B) + rect(2, 6.5, 3, 3, G) + rect(2, 10.5, 3, 3, O)
                 + line(6.5, 4, 14, 4, K, 1.2) + line(6.5, 8, 14, 8, K, 1.2) + line(6.5, 12, 14, 12, K, 1.2))


@icon("list_by_source")
def _(): return (f("M1.5 3h4l1.2 1.5H14V13H1.5z", Y, YD, 1) + line(6.5, 8, 12, 8, K, 1) + line(6.5, 10.5, 12, 10.5, K, 1))


@icon("list_by_visibility")
def _(): return (rect(1.5, 2.5, 3.5, 3.5, W, K, 1) + s("M2.3 4.3l.9 1 1.6-1.9", G, 1.1) + rect(1.5, 9.5, 3.5, 3.5, W, K, 1)
                 + line(7, 4.2, 14, 4.2, K, 1.2) + line(7, 11.2, 14, 11.2, K, 1.2))


@icon("list_by_selection")
def _(): return (rect(1.5, 2.5, 3.5, 3.5, C, K, 1) + rect(1.5, 9.5, 3.5, 3.5, W, K, 1)
                 + line(7, 4.2, 14, 4.2, K, 1.2) + line(7, 11.2, 14, 11.2, K, 1.2))


@icon("catalog")
def _(): return (rect(2, 1.5, 12, 13, "#E9D7B8", OD, 1) + rect(2, 1.5, 12, 4, "#D6B986") + rect(2, 7.5, 12, 1, OD)
                 + rect(6.5, 3, 3, 1.2, K) + rect(6.5, 9.5, 3, 1.2, K))


@icon("folder")
def _(): return f("M1.5 3.5h4.5l1.5 1.5h7v8.5h-13z", Y, YD, 1)


@icon("search")
def _(): return magnifier()


@icon("arctoolbox")
def _(): return toolbox()


@icon("results")
def _(): return page() + s("M5 9l2 2 4-4.5", G, 1.6)


@icon("history")
def _(): return (circ(8, 8, 6.3, W, K, 1.2) + s("M8 4.5V8h3", K, 1.3) + s("M2.5 6.5A6 6 0 0 1 4 4.2", B, 1.6) + f("M1.5 3.5v3.5H5z", B))


@icon("model_builder")
def _(): return (rect(1.5, 6, 4, 4, Y, YD, .9, .8) + circ(10.5, 3.5, 2.2, B, BD, .9) + circ(10.5, 12.5, 2.2, G, GD, .9)
                 + s("M5.5 7.5l3-3M5.5 8.5l3 3", K, 1.1))


@icon("python")
def _(): return (f("M8 1.5c-3 0-3 1.3-3 2.2V5h3.3v.8H3.2C2 5.8 1.5 7 1.5 8s.4 2.3 1.8 2.3h1.3V8.7c0-1.2 1-2.2 2.2-2.2h3c1 0 1.9-.8 1.9-1.9V3.7c0-1.3-1.3-2.2-3.7-2.2z", B)
                 + f("M8 14.5c3 0 3-1.3 3-2.2V11H7.7v-.8h4.9c1.2 0 1.9-1.2 1.9-2.2s-.4-2.3-1.8-2.3h-1.3v1.6c0 1.2-1 2.2-2.2 2.2h-3c-1 0-1.9.8-1.9 1.9v1.9c0 1.3 1.3 2.2 3.7 2.2z", Y)
                 + circ(6.3, 3.3, .6, W) + circ(9.7, 12.7, .6, W))


@icon("symbology")
def _(): return (f("M8 1.5c3.6 0 6.5 2.6 6.5 5.8 0 1.6-1.3 2.2-2.4 2.2h-1.3c-.9 0-1.3.8-.9 1.5.7 1.2.2 3.5-2 3.5C4.4 14.5 1.5 11.6 1.5 8S4.4 1.5 8 1.5z", W, K, 1.1)
                 + circ(5, 6, 1.3, R) + circ(8.5, 4.3, 1.3, Y) + circ(4.5, 9.5, 1.3, B) + circ(11.5, 5.5, 1.3, G))


@icon("labeling")
def _(): return (f("M2 5l5-2 7 3-5 2.5-7-1.5z", GL, GD, 1) + rect(6, 8.5, 8.5, 5, W, K, .9) + text(10.2, 12.5, "ab", 4.5, K, "bold"))


@icon("style_manager")
def _(): return ICONS["symbology"]()


# -- geoprocessing
@icon("buffer")
def _(): return (circ(8, 8, 6, BL, BD, 1, "2 1.2") + f("M5 8l3-1.5L11 8 8 9.5z", G, GD, .8))


@icon("clip")
def _(): return (f("M2 3h7v7H2z", GL, GD, 1) + rect(6, 6, 8, 8, "none", R, 1.2).replace('stroke-width="1.2"', 'stroke-width="1.2" stroke-dasharray="2 1.3"'))


@icon("intersect")
def _(): return polygon_overlay(GL, BL, G)


@icon("union")
def _(): return polygon_overlay(G, G) .replace('stroke="%s" stroke-width="1"' % K, 'stroke="%s" stroke-width="1"' % K)


@icon("merge")
def _(): return (f("M2 5h5v6H2z", GL, GD, 1) + f("M9 5h5v6H9z", BL, BD, 1) + s("M7 8h2", K, 1.5))


@icon("dissolve")
def _(): return (f("M2 3h12v10H2z", G, GD, 1) + s("M8 3v10M2 8h12", GL, .9).replace('stroke-linejoin="round"', 'stroke-linejoin="round" stroke-dasharray="1.5 1.5"'))


@icon("erase")
def _(): return (f("M2 3h8v8H2z", GL, GD, 1) + f("M7 6h7v7H7z", W, R, 1.2))


@icon("spatial_join")
def _(): return (f("M2 4l5-2 7 3-5 2.5-7-1.5z", GL, GD, 1) + table(6, 8.5, 8.5, 6, BL))


@icon("environments")
def _(): return (circ(8, 8, 6, "none", K, 1.6, "2.4 1.6") + circ(8, 8, 2.2, W, K, 1.3))


@icon("raster_calculator")
def _(): return (rect(2, 2, 7, 7, L, K, 1) + rect(2, 2, 3.5, 3.5, BL) + rect(5.5, 5.5, 3.5, 3.5, GL)
                 + s("M10 11h4M12 9v4", K, 1.4) + s("M3 12.5h4", K, 1.4))


@icon("georeferencing")
def _(): return (rect(2, 2, 9, 9, L, K, 1) + rect(2, 2, 4.5, 4.5, BL) + circ(5, 5, 1.8, "none", R, 1.3) + circ(13, 13, 1.8, "none", R, 1.3)
                 + s("M6.5 6.5l5 5", R, 1.1))


# -- customize / help
@icon("reset_layout")
def _(): return (rect(1.5, 2.5, 13, 11, W, K, 1) + rect(1.5, 2.5, 13, 2, BL) + rect(1.5, 4.5, 4, 9, GL)
                 + s("M13.5 7.5a3 3 0 1 1-1-2.2", B, 1.4) + f("M13.8 3.8v2.5h-2.5z", B))


@icon("toolset")
def _(): return (f("M1.5 3.5h4.5l1.5 1.5h7v8.5h-13z", R, RD, 1) + f("M5.5 9.5h5", W, W, 1.2))


@icon("tool")
def _(): return (f("M3 13.5l5.5-5.5 1.5 1.5-5.5 5.5z", K) + f("M9 3a3 3 0 0 1 4 4l-2 .5-1.5-1.5.5-2z", M, K, 1) + rect(8.5, 6.5, 2.5, 2.5, K))


@icon("basemap")
def _(): return (f("M2 5l5-2 7 3-5 2.5-7-1.5z", GL, GD, 1) + f("M2 8l5-2 7 3-5 2.5-7-1.5z", BL, BD, 1) + f("M2 11l5-2 7 3-5 2.5-7-1.5z", W, K, 1))


@icon("stop_editing")
def _(): return pencil(2.5, 13.5, Y) + s("M9.5 9.5l5 5M14.5 9.5l-5 5", R, 1.8)


@icon("connect_folder")
def _(): return f("M1.5 3.5h4.5l1.5 1.5h7v8.5h-13z", Y, YD, 1) + s("M6 9h5M9 7l2 2-2 2", K, 1.4)


@icon("snap_vertex")
def _(): return s("M2 13L8 3l6 10", K, 1.2) + rect(6.5, 1.5, 3, 3, C, K, 1)


@icon("snap_end")
def _(): return s("M3 12L13 4", K, 1.2) + rect(11.5, 2.5, 3, 3, C, K, 1) + rect(1.5, 10.5, 3, 3, W, K, 1)


@icon("snap_edge")
def _(): return s("M2 12L14 4", K, 1.2) + rect(6.5, 6.5, 3, 3, C, K, 1)


@icon("snap_midpoint")
def _(): return s("M2 8h12", K, 1.2) + rect(6.5, 6.5, 3, 3, C, K, 1) + s("M2 5.5v5M14 5.5v5", K, 1.2)


@icon("snap_intersection")
def _(): return s("M2 2l12 12M14 2L2 14", K, 1.2) + rect(6.5, 6.5, 3, 3, C, K, 1)


@icon("draw_polygon")
def _(): return f("M3 12L5 4l7 1 2 6-5 3z", BL, BD, 1.1)


@icon("draw_line")
def _(): return s("M2 12L6 5l4 5 4-7", BD, 1.6)


@icon("draw_marker")
def _(): return circ(8, 8, 4, BL, BD, 1.2)


@icon("draw_text")
def _(): return text(8, 12.5, "A", 13, BD)


@icon("draw_rect_text")
def _(): return rect(1.5, 3.5, 13, 9, W, K, 1) + text(8, 11, "A", 8, BD)


@icon("sort_asc")
def _(): return (s("M4 13V3M1.5 5.5L4 3l2.5 2.5", K, 1.4) + rect(8, 11, 3, 2, K) + rect(8, 7.5, 5, 2, K) + rect(8, 4, 7, 2, K))


@icon("sort_desc")
def _(): return (s("M4 3v10M1.5 10.5L4 13l2.5-2.5", K, 1.4) + rect(8, 3, 7, 2, K) + rect(8, 6.5, 5, 2, K) + rect(8, 10, 3, 2, K))


@icon("field_off")
def _(): return (table(1.5, 2, 10, 11) + s("M9.5 9.5l5 5M14.5 9.5l-5 5", R, 1.8))


@icon("options")
def _(): return (f("M8 1.5l1.3 1.9 2.2-.6.6 2.2 1.9 1.3-1.3 1.7 1.3 1.7-1.9 1.3-.6 2.2-2.2-.6L8 14.5l-1.3-1.9-2.2.6-.6-2.2L2 9.7 3.3 8 2 6.3l1.9-1.3.6-2.2 2.2.6z", M, K, .9)
                 + circ(8, 8, 2.3, W, K, 1))


@icon("customize")
def _(): return ICONS["options"]()


@icon("addins")
def _(): return (f("M3 5h4V3.5a1.5 1.5 0 0 1 3 0V5h3v3h1.5a1.5 1.5 0 0 1 0 3H13v3H3z", B, BD, 1))


@icon("help")
def _(): return circ(8, 8, 6.5, B, BD, 1) + text(8, 11.2, "?", 9.5, W)


@icon("about")
def _(): return circ(8, 8, 6.5, BL, BD, 1) + text(8, 11.2, "i", 9, BD, "bold", "Georgia, serif")


# -- insert
@icon("title")
def _(): return text(8, 12.5, "T", 13, K)


@icon("text")
def _(): return text(8, 12, "A", 12, K)


@icon("north_arrow")
def _(): return (f("M8 1.5l3 11-3-2-3 2z", W, K, 1) + f("M8 1.5l3 11-3-2z", K) + text(8, 15.5, "N", 4, K))


@icon("scale_bar")
def _(): return (rect(1.5, 7, 13, 2.5, W, K, 1) + rect(1.5, 7, 3.25, 2.5, K) + rect(8, 7, 3.25, 2.5, K)
                 + line(1.5, 5, 1.5, 7, K, 1) + line(14.5, 5, 14.5, 7, K, 1))


@icon("picture")
def _(): return (rect(1.5, 2.5, 13, 11, W, K, 1) + f("M2.5 12.5l4-5 3 3 2-2 3 4z", G) + circ(11, 5.5, 1.5, Y))


@icon("grid")
def _(): return (rect(2, 2, 12, 12, "none", K, 1) + line(6, 2, 6, 14, K, .9) + line(10, 2, 10, 14, K, .9)
                 + line(2, 6, 14, 6, K, .9) + line(2, 10, 14, 10, K, .9))


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, fn in sorted(ICONS.items()):
        body = fn()
        with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as fh:
            fh.write(HEAD + body + TAIL + "\n")
    print("wrote %d icons to %s" % (len(ICONS), OUT))


if __name__ == "__main__":
    main()
