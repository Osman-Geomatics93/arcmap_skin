#!/usr/bin/env python3
"""Check a plugin zip the way plugins.qgis.org does before uploading.

    python scripts/validate.py dist/arcmap_skin-0.1.0.zip

Checks: one top-level folder named like the package, __init__.py with
classFactory, metadata.txt with every required field and sane values,
LICENSE present, no __pycache__/.pyc/.git/__MACOSX/binaries, icon path
valid, version format, URLs. Exit code 1 on any error.
"""

import re
import sys
import zipfile

REQUIRED = ["name", "qgisMinimumVersion", "description", "version", "author", "email", "about", "tracker", "repository"]
FORBIDDEN = ("__pycache__", ".pyc", "/.git", "__MACOSX", ".DS_Store", ".exe", ".dll", ".pyd", ".so", "Thumbs.db")


def main(path):
    errors, warnings = [], []
    z = zipfile.ZipFile(path)
    names = z.namelist()
    tops = sorted({n.split("/")[0] for n in names})
    if len(tops) != 1:
        errors.append("zip must contain exactly one top-level folder, found %s" % tops)
        return report(errors, warnings)
    pkg = tops[0]
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", pkg):
        errors.append("top-level folder %r is not a valid Python package name" % pkg)
    for n in names:
        if any(f in n for f in FORBIDDEN):
            errors.append("forbidden file in zip: %s" % n)
    if pkg + "/__init__.py" not in names:
        errors.append("missing %s/__init__.py" % pkg)
    elif b"classFactory" not in z.read(pkg + "/__init__.py"):
        errors.append("__init__.py has no classFactory")
    if pkg + "/metadata.txt" not in names:
        errors.append("missing metadata.txt")
        return report(errors, warnings)
    if pkg + "/LICENSE" not in names and pkg + "/LICENSE.txt" not in names:
        errors.append("missing LICENSE file inside the plugin folder (required since 2024)")
    md = z.read(pkg + "/metadata.txt").decode("utf-8", "replace")
    if not md.lstrip().startswith("[general]"):
        errors.append("metadata.txt must start with [general]")
    fields = dict(re.findall(r"^([A-Za-z_]+)=(.*)$", md, re.M))
    for key in REQUIRED:
        if not fields.get(key, "").strip():
            errors.append("metadata: missing or empty %s" % key)
    version = fields.get("version", "")
    if version and not re.match(r"^\d+(\.\d+){1,3}$", version.strip()):
        errors.append("metadata: version %r should look like 1.2 or 1.2.3" % version)
    for key in ("tracker", "repository", "homepage"):
        url = fields.get(key, "").strip()
        if url and not re.match(r"^https?://", url):
            errors.append("metadata: %s must be an http(s) URL" % key)
        if url and "github.com/mohamedfawzy/arcmap_skin" in url:
            warnings.append("metadata: %s still points at the placeholder repository %s" % (key, url))
    if "@" not in fields.get("email", ""):
        errors.append("metadata: email looks wrong")
    icon = fields.get("icon", "").strip()
    if icon and pkg + "/" + icon not in names:
        errors.append("metadata: icon %r not in zip" % icon)
    qmin = fields.get("qgisMinimumVersion", "").strip()
    if qmin and not re.match(r"^\d+\.\d+$", qmin):
        errors.append("metadata: qgisMinimumVersion %r should be like 3.40" % qmin)
    if fields.get("experimental", "").strip().lower() not in ("", "true", "false"):
        errors.append("metadata: experimental must be True or False")
    size = sum(i.file_size for i in z.infolist())
    if size > 25 * 1024 * 1024:
        warnings.append("uncompressed size is %.1f MB; large plugins upload slowly" % (size / 1e6))
    if len(fields.get("description", "")) > 500:
        warnings.append("description is long; keep it to one or two sentences (about= is for the long text)")
    return report(errors, warnings, "%s %s: %d files" % (fields.get("name"), version, len(names)))


def report(errors, warnings, summary=""):
    if summary:
        print(summary)
    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("ERROR:", e)
    print("OK – ready to upload" if not errors else "%d error(s)" % len(errors))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "dist/arcmap_skin-0.1.0.zip"))
