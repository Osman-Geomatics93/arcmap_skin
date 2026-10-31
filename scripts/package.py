#!/usr/bin/env python3
"""Build dist/arcmap_skin-<version>.zip, the file to upload or install from ZIP."""

import os
import re
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "arcmap_skin")
SKIP_DIRS = {"__pycache__"}
SKIP_EXT = {".pyc", ".ts"}


def version():
    with open(os.path.join(SRC, "metadata.txt"), encoding="utf-8") as fh:
        m = re.search(r"^version=(.+)$", fh.read(), re.M)
    return m.group(1).strip()


def main():
    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "arcmap_skin-%s.zip" % version())
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(SRC):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for name in files:
                if os.path.splitext(name)[1] in SKIP_EXT:
                    continue
                path = os.path.join(root, name)
                arc = os.path.join("arcmap_skin", os.path.relpath(path, SRC))
                zf.write(path, arc)
                count += 1
    print("wrote %s (%d files)" % (out, count))


if __name__ == "__main__":
    main()

