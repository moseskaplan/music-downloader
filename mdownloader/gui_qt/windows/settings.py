"""Settings dialog — configure user preferences (download folder, etc.)."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFileDialog, QDialogButtonBox, QFrame,
)
from PyQt6.QtCore import Qt

from mdownloader.config import load_config, save_config


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = load_config()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self.setFixedWidth(480)

        layout = QVBoxLayout()
        layout.setContentsMargins(32, 32, 32, 24)
        layout.setSpacing(0)
        self.setLayout(layout)

        # ── Title ─────────────────────────────────────────
        title = QLabel("Settings")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        layout.addSpacing(24)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        layout.addSpacing(24)

        # ── Download folder ───────────────────────────────
        section = QLabel("DOWNLOAD FOLDER")
        section.setObjectName("sectionLabel")
        layout.addWidget(section)

        layout.addSpacing(10)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        self._folder_field = QLineEdit(self._config["download_root_dir"])
        self._folder_field.setObjectName("folderField")
        self._folder_field.setReadOnly(True)
        self._folder_field.setFixedHeight(36)
        folder_row.addWidget(self._folder_field)

        btn_choose = QPushButton("Choose…")
        btn_choose.setObjectName("secondaryBtn")
        btn_choose.setFixedHeight(36)
        btn_choose.setFixedWidth(90)
        btn_choose.clicked.connect(self._on_choose_folder)
        folder_row.addWidget(btn_choose)

        layout.addLayout(folder_row)

        layout.addSpacing(8)

        hint = QLabel("Albums will be saved to  <chosen folder> / Artist / Album")
        hint.setObjectName("folderPath")
        layout.addWidget(hint)

        layout.addSpacing(32)

        sep2 = QFrame()
        sep2.setObjectName("separator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        layout.addSpacing(20)

        # ── Buttons ───────────────────────────────────────
        btn_box = QDialogButtonBox()
        btn_cancel = btn_box.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        btn_save = btn_box.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole)

        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.setFixedHeight(38)

        btn_save.setObjectName("primaryBtn")
        btn_save.setFixedHeight(38)

        btn_box.accepted.connect(self._on_save)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box, alignment=Qt.AlignmentFlag.AlignRight)

    # ── Slots ─────────────────────────────────────────────

    def _on_choose_folder(self):
        current = self._folder_field.text()
        chosen = QFileDialog.getExistingDirectory(
            self,
            "Choose Download Folder",
            current,
            QFileDialog.Option.ShowDirsOnly,
        )
        if chosen:
            self._folder_field.setText(chosen)

    def _on_save(self):
        self._config["download_root_dir"] = self._folder_field.text()
        save_config(self._config)
        self.accept()
