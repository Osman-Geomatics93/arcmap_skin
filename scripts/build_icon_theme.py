#!/usr/bin/env python3
"""Build the ArcMap icon theme from QGIS's own icons.

Run with QGIS's Python, which has the icons in its compiled resources::

    "C:/Program Files/QGIS 3.44.6/bin/python-qgis.bat" scripts/build_icon_theme.py

Steps
1. Walk ``:/images/themes/default`` and read every SVG.
2. Flatten gradients to their average colour, map every colour onto the
   ArcMap palette (greys, yellow, blue, green, red, orange, purple) and
   soften the dark outlines QGIS uses.
3. Write the result to ``arcmap_skin/resources/qgis_theme/icons/…``
   keeping QGIS's paths, so the folder is a complete QGIS icon theme.
4. Copy the hand-drawn ArcMap icons over the QGIS icons they replace
   (``ARCMAP_AS_QGIS`` in ``icon_theme.py``) and ``theme_overrides/``.

QGIS icons are GPL-2.0-or-later, as is this plugin.
"""

import colorsys
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "arcmap_skin")
OUT = os.path.join(PKG, "resources", "qgis_theme")
HAND = os.path.join(PKG, "resources", "icons", "arcmap")
OVERRIDES = os.path.join(PKG, "resources", "icons", "theme_overrides")

PALETTE = {
    "red": ("#f3c1bd", "#d0352b", "#9a2018"),
    "orange": ("#fad8ae", "#f0a050", "#c0601a"),
    "yellow": ("#fbe6a2", "#f2b822", "#b08300"),
    "green": ("#cfe3b4", "#3a9e3a", "#23702a"),
    "blue": ("#bbd7f2", "#3b78c4", "#2a5a99"),
    "purple": ("#e3d8f3", "#8a63c4", "#5a3d8a"),
}
GREYS = ("#ffffff", "#dfdfdf", "#959595", "#4a4a4a")

HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")


def to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def to_hex(rgb):
    return "#%02x%02x%02x" % tuple(int(round(c * 255)) for c in rgb)


def arcmap_colour(h):
    r, g, b = to_rgb(h)
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    if sat < 0.2 or light > 0.95 or light < 0.06:
        if light > 0.9:
            return GREYS[0]
        if light > 0.6:
            return GREYS[1]
        if light > 0.3:
            return GREYS[2]
        return GREYS[3]
    deg = hue * 360
    if deg < 15 or deg >= 330:
        fam = "red"
    elif deg < 40:
        fam = "orange"
    elif deg < 70:
        fam = "yellow"
    elif deg < 165:
        fam = "green"
    elif deg < 255:
        fam = "blue"
    else:
        fam = "purple"
    tones = PALETTE[fam]
    if light > 0.72:
        return tones[0]
    if light < 0.3:
        return tones[2]
    return tones[1]


def flatten(text):
    text = re.sub(r"<metadata\b.*?</metadata>", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<sodipodi:namedview\b.*?(/>|</sodipodi:namedview>)", "", text, flags=re.S)
    # gradients → average stop colour
    grads = {}
    for m in re.finditer(r"<(linearGradient|radialGradient)\b([^>]*)>(.*?)</\1>", text, flags=re.S):
        attrs, body = m.group(2), m.group(3)
        gid = re.search(r'\bid="([^"]+)"', attrs)
        if not gid:
            continue
        stops = re.findall(r'stop-color\s*[:=]\s*"?(#[0-9a-fA-F]{3,6})', body)
        href = re.search(r'href="#([^"]+)"', attrs)
        grads[gid.group(1)] = (stops, href.group(1) if href else None)
    for m in re.finditer(r"<(linearGradient|radialGradient)\b([^>]*)/>", text):
        gid = re.search(r'\bid="([^"]+)"', m.group(2))
        href = re.search(r'href="#([^"]+)"', m.group(2))
        if gid:
            grads[gid.group(1)] = ([], href.group(1) if href else None)

    def resolve(gid, depth=0):
        if gid not in grads or depth > 5:
            return None
        stops, href = grads[gid]
        if stops:
            rgbs = [to_rgb(s) for s in stops]
            return to_hex(tuple(sum(c[i] for c in rgbs) / len(rgbs) for i in range(3)))
        return resolve(href, depth + 1) if href else None

    def url_repl(m):
        colour = resolve(m.group(1))
        return colour if colour else "none"

    text = re.sub(r"url\(#([^)]+)\)", url_repl, text)
    return text


def recolour(text):
    text = HEX.sub(lambda m: arcmap_colour(m.group(0)), text)
    text = re.sub(r'(fill|stroke)(\s*[:=]\s*"?)black\b', lambda m: m.group(1) + m.group(2) + GREYS[3], text)
    text = re.sub(r'(fill|stroke)(\s*[:=]\s*"?)white\b', lambda m: m.group(1) + m.group(2) + GREYS[0], text)
    return text


def soften(text):
    """Lighter, tinted outlines instead of QGIS's dark #4a4a4a strokes."""

    def shape(m):
        tag = m.group(0)
        fill = re.search(r'fill\s*[:=]\s*"?(#[0-9a-fA-F]{6}|none)', tag)
        stroke = re.search(r'stroke\s*[:=]\s*"?#4a4a4a', tag)
        if not stroke:
            return tag
        if not fill or fill.group(1) == "none":
            new = "#6b6b6b"
        else:
            r, g, b = to_rgb(fill.group(1))
            h, l, s_ = colorsys.rgb_to_hls(r, g, b)
            if l > 0.9:
                new = "#8f8f8f"
            elif s_ < 0.2:
                new = to_hex(colorsys.hls_to_rgb(h, max(0, l - 0.18), s_))
            else:
                new = to_hex(colorsys.hls_to_rgb(h, l * 0.62, min(s_, 0.85)))
        tag = re.sub(r'(stroke\s*[:=]\s*"?)#4a4a4a', lambda mm: mm.group(1) + new, tag)
        if "stroke-width" not in tag:
            tag = tag.replace("<" + m.group(1), '<%s stroke-width="1.5"' % m.group(1), 1)
        return tag

    text = re.sub(r"<(path|rect|circle|ellipse|polygon|polyline|line)\b[^>]*>", shape, text)
    return text.replace("#4a4a4a", "#666666")


def iter_qgis_icons():
    from qgis.PyQt.QtCore import QDir, QDirIterator, QFile, QIODevice

    it = QDirIterator(":/images/themes/default", ["*.svg"], QDir.Filter.Files, QDirIterator.IteratorFlag.Subdirectories)
    base = ":/images/themes/default/"
    while it.hasNext():
        path = it.next()
        f = QFile(path)
        if not f.open(QIODevice.OpenModeFlag.ReadOnly):
            continue
        data = bytes(f.readAll()).decode("utf-8", "replace")
        f.close()
        yield path[len(base):], data


def hand_drawn_map():
    sys.path.insert(0, ROOT)
    # Import without triggering qgis.gui requirements: read the dict textually.
    src = open(os.path.join(PKG, "icon_theme.py"), encoding="utf-8").read()
    start = src.index("ARCMAP_AS_QGIS = {")
    end = src.index("\n}\n", start) + 3
    ns = {}
    exec(src[start:end], ns)  # noqa: S102  (our own file)
    return ns["ARCMAP_AS_QGIS"]


def main():
    from qgis.core import QgsApplication

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QgsApplication([], False)
    icons_out = os.path.join(OUT, "icons")
    if os.path.isdir(icons_out):
        for root, _dirs, files in os.walk(icons_out):
            for n in files:
                if n.endswith(".svg"):
                    os.remove(os.path.join(root, n))
    os.makedirs(icons_out, exist_ok=True)
    count = 0
    for rel, data in iter_qgis_icons():
        out = os.path.join(icons_out, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(soften(recolour(flatten(data))))
        count += 1
    # overrides and hand-drawn icons win over the derived ones
    if os.path.isdir(OVERRIDES):
        for n in os.listdir(OVERRIDES):
            if n.endswith(".svg"):
                shutil.copyfile(os.path.join(OVERRIDES, n), os.path.join(icons_out, n))
    copied = 0
    for key, names in hand_drawn_map().items():
        src = os.path.join(HAND, key + ".svg")
        if not os.path.exists(src):
            continue
        for name in names:
            dst = os.path.join(icons_out, name + ".svg")
            if not os.path.exists(dst):
                # not a QGIS icon under that name: keep copy anyway (harmless)
                pass
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            copied += 1
    with open(os.path.join(OUT, "style.qss"), "w", encoding="utf-8") as fh:
        fh.write("/* ArcMap Skin icon theme: styling comes from the plugin */\n")
    with open(os.path.join(OUT, "variables.qss"), "w", encoding="utf-8") as fh:
        fh.write("")
    print("restyled %d QGIS icons, copied %d hand-drawn icons -> %s" % (count, copied, OUT))
    app.exitQgis()


if __name__ == "__main__":
    main()
