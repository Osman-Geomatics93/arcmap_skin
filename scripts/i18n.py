#!/usr/bin/env python3
"""Translations without Qt's lrelease.

    "C:/Program Files/QGIS 3.44.6/bin/python-qgis.bat" scripts/i18n.py [lang]

1. Collects every translatable string: ``tr("…")`` literals in the sources
   plus the caption tables (menus, toolbars, panes, toolbox, …).
2. Reads ``arcmap_skin/i18n/arcmap_skin_<lang>.json`` (``{"English": "…"}``).
3. Writes ``arcmap_skin_<lang>.ts`` (Qt Linguist XML, for editing) and
   ``arcmap_skin_<lang>.qm`` (the binary file QTranslator loads), written by
   a small writer that follows Qt's .qm format, so no Qt tools are needed.
4. Prints the strings still missing from the JSON.
"""

import json
import os
import re
import struct
import sys
import xml.sax.saxutils as sax

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "arcmap_skin")
I18N = os.path.join(PKG, "i18n")
CONTEXT = "ArcMapSkin"

TR_RE = re.compile(r'\btr\(\s*(["\'])((?:\\.|(?!\1).)*)\1')


def literal_strings():
    out = set()
    for name in os.listdir(PKG):
        if not name.endswith(".py"):
            continue
        with open(os.path.join(PKG, name), encoding="utf-8") as fh:
            src = fh.read()
        for m in TR_RE.finditer(src):
            text = m.group(2).encode("utf-8").decode("unicode_escape") if "\\" in m.group(2) else m.group(2)
            out.add(text)
    return out


def table_strings():
    """Captions passed to tr() through data tables."""
    sys.path.insert(0, ROOT)
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from arcmap_skin import arctoolbox, contents_views, dialogs, editing, mapview, menus, panes, query_builder, toolbars

    out = set()
    out |= {text for text, _ in menus.ALIASES.values()}
    for _, title, items in menus.MENUS:
        out.add(title)
        out |= _walk_items(items)
    for _, title, items in toolbars.TOOLBARS:
        out.add(title)
        out |= _walk_items(items)
    out |= set(toolbars.RENAMED_NATIVE.values())
    out |= {title for title, _, _ in panes.PANES.values()}
    for toolbox, toolsets in arctoolbox.TOOLBOXES:
        out.add(toolbox)
        for toolset, tools in toolsets:
            out.add(toolset)
            out |= {name for name, _ in tools}
    out |= set(arctoolbox.TOOLBOX_ORDER)
    for rules in arctoolbox.GROUP_RULES.values():
        for toolbox, toolset in rules.values():
            out.add(toolbox)
            out.add(toolset)
    out |= set(mapview.UNIT_NAMES.values())
    out |= {text for _, text in mapview.UNIT_FORMATS}
    out |= set(dialogs.LAYER_PAGES.values())
    out |= set(dialogs.RENDERERS.values())
    from arcmap_skin import attribute_table

    out |= {entry[2] for entry in attribute_table.TOOLBAR if entry}
    out |= {entry[2] for entry in attribute_table.TABLE_OPTIONS if entry}
    out |= {tip for _, tip, _ in contents_views.VIEWS}
    out |= {caption for _, _, caption in editing.CreateFeaturesDock.CONSTRUCTION}
    out |= {tip for _, tip, _ in editing.SnappingToolBar.TOGGLES}
    out |= {text for text, _ in query_builder.METHODS}
    return out


def _walk_items(items):
    out = set()
    for item in items:
        if isinstance(item, tuple):
            kind = item[0]
            if kind in ("alias", "menu", "dock", "toolbar"):
                out.add(item[2])
            elif kind == "sub":
                out.add(item[1])
                out |= _walk_items(item[3] if len(item) > 3 else item[2])
            elif kind == "menubtn":
                out.add(item[2])
                out |= _walk_items(item[4])
    return out


def all_strings():
    return sorted(literal_strings() | table_strings())


# ------------------------------------------------------------------ .qm

MAGIC = bytes([0x3C, 0xB8, 0x64, 0x18, 0xCA, 0xEF, 0x9C, 0x95, 0xCD, 0x21, 0x1C, 0xBF, 0x60, 0xA1, 0xBD, 0xDD])
TAG_END, TAG_TRANSLATION, TAG_SOURCETEXT, TAG_CONTEXT, TAG_COMMENT = 1, 3, 6, 7, 8
SEC_CONTEXTS, SEC_HASHES, SEC_MESSAGES = 0x2F, 0x42, 0x69


def elf_hash(data):
    """Qt's elfHash (qtranslator.cpp): note the >> 24, not the classic 23."""
    h = 0
    for byte in data:
        h = ((h << 4) + byte) & 0xFFFFFFFF
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xFFFFFFFF
    return h or 1


def write_qm(path, translations, context=CONTEXT):
    """Write a .qm that QTranslator loads; ``translations`` is {source: target}."""
    messages = bytearray()
    index = []
    ctx = context.encode("utf-8")
    for source, target in sorted(translations.items()):
        if not target:
            continue
        offset = len(messages)
        src = source.encode("utf-8")
        tr16 = target.encode("utf-16-be")
        messages += bytes([TAG_TRANSLATION]) + struct.pack(">I", len(tr16)) + tr16
        messages += bytes([TAG_SOURCETEXT]) + struct.pack(">I", len(src)) + src
        messages += bytes([TAG_CONTEXT]) + struct.pack(">I", len(ctx)) + ctx
        messages += bytes([TAG_END])
        index.append((elf_hash(src), offset))
    index.sort()
    hashes = b"".join(struct.pack(">II", h, o) for h, o in index)
    out = bytearray(MAGIC)
    out += bytes([SEC_HASHES]) + struct.pack(">I", len(hashes)) + hashes
    out += bytes([SEC_MESSAGES]) + struct.pack(">I", len(messages)) + messages
    with open(path, "wb") as fh:
        fh.write(out)
    return len(index)


def write_ts(path, lang, strings, translations):
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<!DOCTYPE TS>", '<TS version="2.1" language="%s">' % lang,
             "<context>", "    <name>%s</name>" % CONTEXT]
    for source in strings:
        target = translations.get(source, "")
        lines.append("    <message>")
        lines.append("        <source>%s</source>" % sax.escape(source))
        if target:
            lines.append("        <translation>%s</translation>" % sax.escape(target))
        else:
            lines.append('        <translation type="unfinished"></translation>')
        lines.append("    </message>")
    lines += ["</context>", "</TS>", ""]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main(argv):
    lang = argv[0] if argv else "ar"
    os.makedirs(I18N, exist_ok=True)
    strings = all_strings()
    json_path = os.path.join(I18N, "arcmap_skin_%s.json" % lang)
    translations = {}
    if os.path.exists(json_path):
        with open(json_path, encoding="utf-8") as fh:
            translations = json.load(fh)
    # Strings built by implicit concatenation are only complete in the JSON.
    strings = sorted(set(strings) | set(translations))
    write_ts(os.path.join(I18N, "arcmap_skin_%s.ts" % lang), lang, strings, translations)
    n = write_qm(os.path.join(I18N, "arcmap_skin_%s.qm" % lang), {s: translations.get(s, "") for s in strings})
    missing = [s for s in strings if not translations.get(s)]
    print("%d strings, %d translated, %d missing -> %s" % (len(strings), n, len(missing), I18N))
    if "--list-missing" in argv or missing and len(missing) < 400:
        with open(os.path.join(I18N, "missing_%s.txt" % lang), "w", encoding="utf-8") as fh:
            fh.write("\n".join(missing) + "\n")
        print("missing strings written to missing_%s.txt" % lang)


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if not a.startswith("--")] + [a for a in sys.argv[1:] if a.startswith("--")])
