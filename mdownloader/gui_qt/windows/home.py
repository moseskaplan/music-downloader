"""Home screen — entry point for the two main workflows and settings."""

import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt

from mdownloader.config import load_config


class HomeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._config = load_config()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Music Downloader")
        self.setMinimumWidth(500)
        self.setFixedWidth(500)

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(0)
        self.setLayout(layout)

        # ── Title ────────────────────────────────────────
        title = QLabel("Music Downloader")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        layout.addSpacing(8)

        subtitle = QLabel("Download albums and tracks from\nApple Music, Wikipedia & YouTube")
        subtitle.setObjectName("appSubtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(28)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        layout.addSpacing(28)

        # ── Workflow buttons ──────────────────────────────
        section = QLabel("CHOOSE WORKFLOW")
        section.setObjectName("sectionLabel")
        layout.addWidget(section)

        layout.addSpacing(12)

        btn_album = QPushButton("  Album")
        btn_album.setObjectName("primaryBtn")
        btn_album.setFixedHeight(52)
        btn_album.clicked.connect(self._on_album)
        layout.addWidget(btn_album)

        layout.addSpacing(10)

        btn_links = QPushButton("  Individual Link(s)")
        btn_links.setObjectName("primaryBtn")
        btn_links.setFixedHeight(52)
        btn_links.clicked.connect(self._on_individual_links)
        layout.addWidget(btn_links)

        layout.addSpacing(10)

        btn_settings = QPushButton("  Settings")
        btn_settings.setObjectName("secondaryBtn")
        btn_settings.setFixedHeight(42)
        btn_settings.clicked.connect(self._on_settings)
        layout.addWidget(btn_settings)

        layout.addSpacing(28)

        sep2 = QFrame()
        sep2.setObjectName("separator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        layout.addSpacing(16)

        # ── Download folder ───────────────────────────────
        folder_section = QLabel("DOWNLOAD FOLDER")
        folder_section.setObjectName("sectionLabel")
        layout.addWidget(folder_section)

        layout.addSpacing(6)

        self._folder_label = QLabel(self._config["download_root_dir"])
        self._folder_label.setObjectName("folderPath")
        self._folder_label.setWordWrap(True)
        layout.addWidget(self._folder_label)

        layout.addSpacing(6)

        btn_open = QPushButton("Open Folder")
        btn_open.setObjectName("linkBtn")
        btn_open.setFixedHeight(24)
        btn_open.clicked.connect(self._on_open_folder)
        layout.addWidget(btn_open)

        layout.addSpacing(20)

    # ── Slots ─────────────────────────────────────────────

    def _on_album(self):
        from mdownloader.gui_qt.windows.album_flow import AlbumFlowWindow
        self._album_window = AlbumFlowWindow()
        self._album_window.show()

    def _on_individual_links(self):
        from mdownloader.gui_qt.windows.links_flow import LinksFlowWindow
        self._links_window = LinksFlowWindow()
        self._links_window.show()

    def _on_settings(self):
        from mdownloader.gui_qt.windows.settings import SettingsDialog
        dialog = SettingsDialog(parent=self)
        if dialog.exec():
            self.refresh_folder_label()

    def _on_open_folder(self):
        folder = Path(self._config["download_root_dir"]).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(folder)])

    def refresh_folder_label(self):
        """Call this after saving new config to update the displayed path."""
        self._config = load_config()
        self._folder_label.setText(self._config["download_root_dir"])
