# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Music Downloader macOS .app bundle."""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ── Explicitly collect Qt6 plugins from the arm64 miniforge environment ───────
# Pin directly to the miniforge PyQt6 plugins — clean arm64, no Qt5 present.
# NOTE: This path is machine-specific. If rebuilding on a different machine,
# update this to match your local PyQt6 installation path.
_QT6_PLUGINS = "/Users/moseskaplan/miniforge-arm64/lib/python3.13/site-packages/PyQt6/Qt6/plugins"

pyqt6_datas = [
    # macOS window system plugin — required for any GUI to appear
    (f"{_QT6_PLUGINS}/platforms/libqcocoa.dylib",   "PyQt6/Qt6/plugins/platforms"),
    # Minimal/offscreen fallbacks (small, harmless to include)
    (f"{_QT6_PLUGINS}/platforms/libqminimal.dylib", "PyQt6/Qt6/plugins/platforms"),
    (f"{_QT6_PLUGINS}/platforms/libqoffscreen.dylib", "PyQt6/Qt6/plugins/platforms"),
    # Widget styles (macOS native look)
    (f"{_QT6_PLUGINS}/styles",                      "PyQt6/Qt6/plugins/styles"),
    # Image format support (icons, etc.)
    (f"{_QT6_PLUGINS}/imageformats",                "PyQt6/Qt6/plugins/imageformats"),
]

# ── Hidden imports ────────────────────────────────────────────────────────────
# PyInstaller's static analysis misses dynamically imported modules.
# collect_submodules() ensures every sub-module in a package is included.
hidden = (
    collect_submodules("mdownloader")   # all app subpackages
    + collect_submodules("yt_dlp")      # yt-dlp has ~300 extractor modules loaded dynamically
    + collect_submodules("mutagen")     # codec submodules loaded at runtime
    + collect_submodules("bs4")
    + collect_submodules("lxml")
    + collect_submodules("rapidfuzz")
    + [
        "PyQt6.sip",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtNetwork",
    ]
)

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["mdownloader/__main__.py"],        # entry point
    pathex=["."],                       # project root on sys.path
    binaries=[
        ("/usr/local/bin/ffmpeg", "."), # bundle ffmpeg at _MEIPASS root
    ],
    datas=pyqt6_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=["rthook_qt.py"],     # sets QT_QPA_PLATFORM_PLUGIN_PATH
    excludes=[
        "tkinter",                      # not used; saves ~3 MB
        "matplotlib",
        "numpy",
        "scipy",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# ── Executable ────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MusicDownloader",
    debug=False,
    strip=False,
    upx=False,          # UPX can break signed macOS binaries; leave off for now
    console=False,      # no terminal window (windowed app)
    argv_emulation=False,   # must be False for PyQt6 on macOS
)

# ── Collect all binaries + datas into one folder ──────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MusicDownloader",
)

# ── macOS .app bundle ─────────────────────────────────────────────────────────
app = BUNDLE(
    coll,
    name="Music Downloader.app",
    icon="assets/icons/icon.icns",
    bundle_identifier="com.moseskaplan.music-downloader",
    version="0.1.0",
    info_plist={
        "CFBundleName": "Music Downloader",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "10.13.0",
        "NSRequiresAquaSystemAppearance": False,   # allows dark mode
    },
)
