# -*- coding: utf-8 -*-
"""ArcMap Skin: an ArcMap 10 look for QGIS.

This file is the plugin entry point. QGIS calls ``classFactory`` and keeps
the returned object alive for the lifetime of the plugin.

ArcMap Skin is licensed under the GNU General Public License v2 or later.
It is not affiliated with, sponsored or endorsed by Esri.
"""

import os

from qgis.PyQt.QtCore import QCoreApplication, QLocale, QSettings, QTranslator


def _install_translator():
    """Install the plugin translation for the QGIS UI language, if present."""
    locale = QSettings().value("locale/userLocale", QLocale.system().name())
    if not isinstance(locale, str) or not locale:
        return None
    lang = locale.split("_")[0]
    path = os.path.join(os.path.dirname(__file__), "i18n", "arcmap_skin_%s.qm" % lang)
    if not os.path.exists(path):
        return None
    translator = QTranslator()
    if translator.load(path):
        QCoreApplication.installTranslator(translator)
        return translator
    return None


def classFactory(iface):  # noqa: N802  (QGIS API name)
    translator = _install_translator()
    # Imported after the translator so that specs translated at import time
    # pick up the right language.
    from .plugin import ArcMapSkinPlugin

    return ArcMapSkinPlugin(iface, translator)
