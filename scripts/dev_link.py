#!/usr/bin/env python3
"""Link the plugin folder into a QGIS profile for development.

    python scripts/dev_link.py            # default profile
    python scripts/dev_link.py myprofile  # another profile
    python scripts/dev_link.py --remove

On Windows a directory junction is created (no admin rights needed); on
other systems a symlink. Afterwards enable "ArcMap Skin" in the plugin
manager and use Plugin Reloader while developing.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "arcmap_skin")


def profiles_dir():
    if sys.platform.startswith("win"):
        base = os.path.join(os.environ["APPDATA"], "QGIS", "QGIS3", "profiles")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/QGIS/QGIS3/profiles")
    else:
        base = os.path.expanduser("~/.local/share/QGIS/QGIS3/profiles")
    return base


def main(argv):
    remove = "--remove" in argv
    base = None
    for a in argv:
        if a.startswith("--profiles-path="):
            base = a.split("=", 1)[1]
    args = [a for a in argv if not a.startswith("--")]
    profile = args[0] if args else "default"
    # --profiles-path=<dir> targets a separate profile store (what the test
    # runners use with "qgis-bin.exe --profiles-path <dir>"), so the user's
    # own profiles.ini is never touched by test runs.
    plugins = os.path.join(base or profiles_dir(), profile, "python", "plugins")
    os.makedirs(plugins, exist_ok=True)
    target = os.path.join(plugins, "arcmap_skin")
    if os.path.lexists(target):
        if os.path.islink(target) or _is_junction(target):
            os.rmdir(target) if sys.platform.startswith("win") else os.unlink(target)
            print("removed", target)
        else:
            print("ERROR: %s exists and is a real folder; move it away first" % target)
            return 1
    if remove:
        return 0
    if sys.platform.startswith("win"):
        subprocess.check_call(["cmd", "/c", "mklink", "/J", target, SRC])
    else:
        os.symlink(SRC, target)
    print("linked", target, "->", SRC)
    return 0


def _is_junction(path):
    try:
        return bool(os.lstat(path).st_file_attributes & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    except (AttributeError, OSError):
        return False


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
