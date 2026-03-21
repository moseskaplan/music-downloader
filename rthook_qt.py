"""Runtime hook: lock Qt to its bundled Qt6 plugins, block any system Qt5 plugins.

Runs before any app code. Sets:
  QT_PLUGIN_PATH            — root plugin search path (overrides system Qt5 path)
  QT_QPA_PLATFORM_PLUGIN_PATH — explicit path to the bundled cocoa platform plugin

Both must be set to prevent Qt from falling back to any system plugin location.
"""
import os
import sys

if getattr(sys, "frozen", False):
    _bundle = sys._MEIPASS
    _qt6_plugins_root = os.path.join(_bundle, "PyQt6", "Qt6", "plugins")
    _qt6_platforms = os.path.join(_qt6_plugins_root, "platforms")

    # Override the root plugin search path so Qt never falls back to system Qt5
    os.environ["QT_PLUGIN_PATH"] = _qt6_plugins_root

    # Also pin the platform plugin directory explicitly
    if os.path.isdir(_qt6_platforms):
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = _qt6_platforms
