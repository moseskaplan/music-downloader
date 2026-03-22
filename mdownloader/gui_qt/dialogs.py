"""Shared custom dialogs for Music Downloader."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QMessageBox,
)

from mdownloader.config import load_config
from mdownloader.gui_qt.style import ACCENT


_COLOR_SUCCESS = ACCENT      # neon green
_COLOR_FAILURE = "#ff4444"   # red


class DownloadResultDialog(QDialog):
    """Styled completion dialog shown after a download run finishes.

    Displays a neon-green border on full success, red border on any failure.
    Provides 'Open Folder' and 'Close' buttons.

    Usage:
        dlg = DownloadResultDialog(success, fail, output_dir, parent=self)
        dlg.exec()
        if fail == 0:
            self.close()
    """

    def __init__(
        self,
        success: int,
        fail: int,
        output_dir: Path | None,
        parent=None,
    ):
        super().__init__(parent)
        self._output_dir = output_dir
        self._is_success = fail == 0
        accent = _COLOR_SUCCESS if self._is_success else _COLOR_FAILURE
        self._setup_ui(success, fail, accent)

    def _setup_ui(self, success: int, fail: int, accent: str) -> None:
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setMinimumWidth(420)
        self.setStyleSheet(
            f"QDialog {{ background-color: #111111; border: 2px solid {accent}; border-radius: 8px; }}"
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Title
        if self._is_success:
            title_text = "✓  Download Complete"
        else:
            title_text = "✗  Download Incomplete"

        title = QLabel(title_text)
        title.setStyleSheet(
            f"QLabel {{ color: {accent}; font-size: 17px; font-weight: 700; "
            f"background: transparent; border: none; }}"
        )
        layout.addWidget(title)

        layout.addSpacing(16)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {accent}; background-color: {accent}; border: none; max-height: 1px;")
        layout.addWidget(sep)

        layout.addSpacing(16)

        # Body text
        if self._is_success:
            body_text = (
                f"All {success} track{'s' if success != 1 else ''} downloaded successfully."
            )
        else:
            body_text = (
                f"{fail} track{'s' if fail != 1 else ''} failed to download.\n"
                f"{success} track{'s' if success != 1 else ''} succeeded.\n\n"
                f"Failed tracks are shown in red in the table."
            )

        body = QLabel(body_text)
        body.setStyleSheet("QLabel { color: #cccccc; font-size: 14px; background: transparent; border: none; }")
        body.setWordWrap(True)
        layout.addWidget(body)

        if self._output_dir:
            layout.addSpacing(12)
            path_label = QLabel(f"Saved to:\n{self._output_dir}")
            path_label.setStyleSheet(
                "QLabel { color: #888888; font-size: 12px; background: transparent; border: none; }"
            )
            path_label.setWordWrap(True)
            layout.addWidget(path_label)

        layout.addSpacing(24)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        if self._output_dir:
            open_btn = QPushButton("Open Folder")
            open_btn.setObjectName("secondaryBtn")
            open_btn.setFixedHeight(38)
            open_btn.clicked.connect(self._on_open_folder)
            btn_row.addWidget(open_btn)

        # "Send to Drive" — only shown on success and when Google Drive folder is configured
        if self._is_success and self._output_dir:
            gd_dir = load_config().get("google_drive_music_dir", "").strip()
            if gd_dir:
                self._gd_dir = Path(gd_dir)
                drive_btn = QPushButton("Send to Drive")
                drive_btn.setObjectName("secondaryBtn")
                drive_btn.setFixedHeight(38)
                drive_btn.clicked.connect(self._on_send_to_drive)
                btn_row.addWidget(drive_btn)

        btn_row.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(38)
        close_btn.setFixedWidth(100)
        close_btn.setStyleSheet(
            f"QPushButton {{ color: {accent}; border: 2px solid {accent}; "
            f"background-color: transparent; border-radius: 6px; "
            f"font-size: 14px; font-weight: 600; padding: 4px 16px; }}"
            f"QPushButton:hover {{ background-color: #1a1a1a; }}"
            f"QPushButton:pressed {{ background-color: #222222; }}"
        )
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _on_open_folder(self) -> None:
        if self._output_dir:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(["open", str(self._output_dir)])

    def _on_send_to_drive(self) -> None:
        src_files = list(self._output_dir.glob("*.mp3"))
        if not src_files:
            QMessageBox.warning(self, "No Files", "No MP3 files found in the download folder.")
            return

        # Check for conflicts
        conflicts = [f for f in src_files if (self._gd_dir / f.name).exists()]

        if conflicts:
            names = "\n".join(f"  • {f.name}" for f in conflicts)
            msg = QMessageBox(self)
            msg.setWindowTitle("Files Already Exist")
            msg.setText(
                f"The following {len(conflicts)} file{'s' if len(conflicts) != 1 else ''} "
                f"already exist in the Google Drive folder:\n\n{names}\n\n"
                f"What would you like to do?"
            )
            overwrite_btn = msg.addButton("Overwrite All", QMessageBox.ButtonRole.AcceptRole)
            skip_btn = msg.addButton("Skip Conflicts", QMessageBox.ButtonRole.ActionRole)
            msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            msg.exec()

            clicked = msg.clickedButton()
            if clicked is overwrite_btn:
                files_to_copy = src_files
            elif clicked is skip_btn:
                conflict_names = {f.name for f in conflicts}
                files_to_copy = [f for f in src_files if f.name not in conflict_names]
            else:
                return  # Cancel
        else:
            files_to_copy = src_files

        self._gd_dir.mkdir(parents=True, exist_ok=True)
        copied = 0
        for f in files_to_copy:
            shutil.copy2(f, self._gd_dir / f.name)
            copied += 1

        skipped = len(src_files) - copied
        msg_parts = [f"{copied} track{'s' if copied != 1 else ''} sent to Drive."]
        if skipped:
            msg_parts.append(f"{skipped} skipped.")
        QMessageBox.information(self, "Sent to Drive", " ".join(msg_parts))
