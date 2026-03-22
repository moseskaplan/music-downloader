# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Music Downloader Windows build.

Run from the repo root on a Windows machine:
    pip install pyinstaller
    pyinstaller MusicDownloader-Windows.spec

ffmpeg must be available at C:\\ffmpeg\\bin\\ffmpeg.exe before building.
Download a Windows build from https://www.gyan.dev/ffmpeg/builds/
and extract it so that path exists, or update the path below.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ── Hidden imports ────────────────────────────────────────────────────────────
hidden = (
    collect_submodules("mdownloader")
    + collect_submodules("yt_dlp")
    + collect_submodules("mutagen")
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
    ["mdownloader/__main__.py"],
    pathex=["."],
    binaries=[
        # Bundle ffmpeg.exe — update path if your ffmpeg is installed elsewhere
        ("C:\\ffmpeg\\bin\\ffmpeg.exe", "."),
    ],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
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
    upx=False,
    console=False,      # no terminal window
    icon="assets\\icons\\icon.ico",  # see note below on icon conversion
)

# ── Collect into one folder ───────────────────────────────────────────────────
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="MusicDownloader",
)
