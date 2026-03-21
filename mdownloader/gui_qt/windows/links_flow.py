"""Individual Links download workflow: URL list → metadata preview → download."""

import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QMessageBox, QStackedWidget, QSizePolicy, QScrollArea, QApplication,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QCursor, QColor


class _TrackTable(QTableWidget):
    """QTableWidget with Enter-to-edit keyboard navigation.

    - Enter on a selected (non-editing) cell starts editing (Title col only).
    - Enter while editing commits the value and moves selection down one row.
    """

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.state() != QAbstractItemView.State.EditingState:
                idx = self.currentIndex()
                if idx.isValid() and bool(idx.flags() & Qt.ItemFlag.ItemIsEditable):
                    self.edit(idx)
                    return
        super().keyPressEvent(event)

from mdownloader.config import load_config
from mdownloader.core.utils import clean_filename, is_valid_youtube_url
from mdownloader.gui_qt.style import ACCENT, TEXT_MUTED

# Metadata table column indices
_COL_TITLE = 0
_COL_ARTIST = 1
_COL_DURATION = 2
_COL_STATUS = 3

_STATUS_PENDING = "Pending"
_STATUS_DOWNLOADING = "Downloading"
_STATUS_DONE = "Downloaded"
_STATUS_FAILED = "Failed"


class LinksFlowWindow(QWidget):
    """Two-screen flow: URL list input → metadata table → download."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracks: list[dict] = []
        self._output_dir = None
        self._worker = None
        self._fetch_worker = None
        self._download_total = 0
        self._download_progress = 0
        # Each entry is (QLineEdit, QCheckBox) for url + playlist toggle
        self._url_rows: list[tuple[QLineEdit, QCheckBox]] = []
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Music Downloader — Individual Links")
        self.setMinimumSize(QSize(720, 520))

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setLayout(root_layout)

        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack)

        self._stack.addWidget(self._build_url_screen())    # index 0
        self._stack.addWidget(self._build_table_screen())  # index 1
        self._stack.setCurrentIndex(0)

    # ── Screen 0: URL input list ──────────────────────────────────────────────

    def _build_url_screen(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(0)
        page.setLayout(layout)

        title = QLabel("Individual Links")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        layout.addSpacing(8)

        subtitle = QLabel(
            "Paste one YouTube URL per track.\n"
            "Check  Playlist  to fetch all tracks from a YouTube playlist (up to 50)."
        )
        subtitle.setObjectName("appSubtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(28)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        layout.addSpacing(24)

        url_label = QLabel("YOUTUBE URLS")
        url_label.setObjectName("sectionLabel")
        layout.addWidget(url_label)

        layout.addSpacing(10)

        # Scrollable container for URL rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(220)

        self._url_rows_widget = QWidget()
        self._url_rows_layout = QVBoxLayout()
        self._url_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._url_rows_layout.setSpacing(8)
        self._url_rows_widget.setLayout(self._url_rows_layout)
        scroll.setWidget(self._url_rows_widget)
        layout.addWidget(scroll)

        layout.addSpacing(10)

        self._add_url_row()   # Start with one row

        add_btn = QPushButton("+ Add Another URL")
        add_btn.setObjectName("linkBtn")
        add_btn.setFixedHeight(28)
        add_btn.clicked.connect(self._add_url_row)
        layout.addWidget(add_btn)

        layout.addSpacing(24)

        sep2 = QFrame()
        sep2.setObjectName("separator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        layout.addSpacing(20)

        self._fetch_btn = QPushButton("Get Track(s)")
        self._fetch_btn.setObjectName("primaryBtn")
        self._fetch_btn.setFixedHeight(48)
        self._fetch_btn.clicked.connect(self._on_fetch)
        layout.addWidget(self._fetch_btn)

        layout.addStretch()

        back_btn = QPushButton("← Back to Home")
        back_btn.setObjectName("linkBtn")
        back_btn.setFixedHeight(28)
        back_btn.clicked.connect(self.close)
        layout.addWidget(back_btn)

        return page

    def _add_url_row(self) -> None:
        row_widget = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        row_widget.setLayout(row_layout)

        url_input = QLineEdit()
        url_input.setObjectName("urlInput")
        url_input.setPlaceholderText("https://www.youtube.com/watch?v=… or playlist URL")
        url_input.setFixedHeight(36)
        row_layout.addWidget(url_input)

        playlist_check = QCheckBox("Playlist")
        playlist_check.setFixedHeight(36)
        row_layout.addWidget(playlist_check)

        remove_btn = QPushButton("✕")
        remove_btn.setObjectName("linkBtn")
        remove_btn.setFixedSize(28, 36)
        remove_btn.clicked.connect(lambda: self._remove_url_row(url_input, playlist_check, row_widget))
        row_layout.addWidget(remove_btn)

        self._url_rows_layout.addWidget(row_widget)
        self._url_rows.append((url_input, playlist_check))
        self._update_remove_buttons()

    def _remove_url_row(self, url_input: QLineEdit, playlist_check: QCheckBox, row_widget: QWidget) -> None:
        if len(self._url_rows) <= 1:
            return
        self._url_rows.remove((url_input, playlist_check))
        self._url_rows_layout.removeWidget(row_widget)
        row_widget.deleteLater()
        self._update_remove_buttons()

    def _update_remove_buttons(self) -> None:
        """Disable remove buttons when only one row remains."""
        only_one = len(self._url_rows) == 1
        for i in range(self._url_rows_layout.count()):
            item = self._url_rows_layout.itemAt(i)
            if item and item.widget():
                for btn in item.widget().findChildren(QPushButton):
                    btn.setEnabled(not only_one)

    # ── Screen 1: metadata table + download ───────────────────────────────────

    def _build_table_screen(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(0)
        page.setLayout(layout)

        self._table_title = QLabel("Ready to Download")
        self._table_title.setObjectName("appTitle")
        layout.addWidget(self._table_title)

        layout.addSpacing(4)

        self._table_subtitle = QLabel()
        self._table_subtitle.setObjectName("appSubtitle")
        layout.addWidget(self._table_subtitle)

        layout.addSpacing(12)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        layout.addSpacing(12)

        self._table = _TrackTable()
        self._table.setObjectName("trackTable")
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Title", "Artist", "Duration", "Status"])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hdr.resizeSection(_COL_TITLE, 240)
        hdr.resizeSection(_COL_ARTIST, 160)
        hdr.resizeSection(_COL_DURATION, 80)
        hdr.resizeSection(_COL_STATUS, 100)
        hdr.setMinimumSectionSize(60)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked |
            QTableWidget.EditTrigger.SelectedClicked |
            QTableWidget.EditTrigger.AnyKeyPressed
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._table)

        layout.addSpacing(6)

        edit_hint = QLabel("Press Enter or double-click a title to edit it before downloading.")
        edit_hint.setObjectName("folderPath")
        layout.addWidget(edit_hint)

        layout.addSpacing(10)

        sep2 = QFrame()
        sep2.setObjectName("separator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        layout.addSpacing(16)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._table_back_btn = QPushButton("← Back")
        self._table_back_btn.setObjectName("secondaryBtn")
        self._table_back_btn.setFixedHeight(42)
        self._table_back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        btn_row.addWidget(self._table_back_btn)

        self._table_home_btn = QPushButton("Return to Home")
        self._table_home_btn.setObjectName("secondaryBtn")
        self._table_home_btn.setFixedHeight(42)
        self._table_home_btn.clicked.connect(self.close)
        btn_row.addWidget(self._table_home_btn)

        btn_row.addStretch()

        self._download_btn = QPushButton("Confirm & Download")
        self._download_btn.setObjectName("downloadBtn")
        self._download_btn.setFixedHeight(42)
        self._download_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(self._download_btn)

        layout.addLayout(btn_row)

        return page

    def _populate_table(self) -> None:
        self._table.setRowCount(len(self._tracks))
        _ro = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        _rw = _ro | Qt.ItemFlag.ItemIsEditable

        for row, track in enumerate(self._tracks):
            title_item = QTableWidgetItem(track.get("track_title", ""))
            title_item.setFlags(_rw)
            self._table.setItem(row, _COL_TITLE, title_item)

            artist_item = QTableWidgetItem(track.get("artist_name", ""))
            artist_item.setFlags(_ro)
            self._table.setItem(row, _COL_ARTIST, artist_item)

            dur_item = QTableWidgetItem(track.get("track_duration", ""))
            dur_item.setFlags(_ro)
            self._table.setItem(row, _COL_DURATION, dur_item)

            status_item = QTableWidgetItem(_STATUS_PENDING)
            status_item.setFlags(_ro)
            status_item.setForeground(QColor(TEXT_MUTED))
            self._table.setItem(row, _COL_STATUS, status_item)

        count = len(self._tracks)
        self._table_title.setText(f"{count} Track{'s' if count != 1 else ''} Ready")

        # Subtitle: use playlist name if all tracks share one, else artist logic
        playlist_names = {t["album_name"] for t in self._tracks if t["album_name"] != "Singles"}
        artists = {t["artist_name"] for t in self._tracks}
        if len(playlist_names) == 1:
            self._table_subtitle.setText(f"Playlist: {next(iter(playlist_names))}")
        elif len(playlist_names) > 1:
            self._table_subtitle.setText(f"{len(playlist_names)} playlists")
        elif len(artists) == 1:
            self._table_subtitle.setText(f"Artist: {next(iter(artists))}")
        else:
            self._table_subtitle.setText(f"{len(artists)} artists · saved to Singles/Mixed/")

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_fetch(self) -> None:
        tasks = [
            (inp.text().strip(), chk.isChecked())
            for inp, chk in self._url_rows
            if inp.text().strip()
        ]
        if not tasks:
            QMessageBox.warning(self, "No URLs", "Please paste at least one YouTube URL.")
            return

        invalid = [url for url, _ in tasks if not is_valid_youtube_url(url)]
        if invalid:
            QMessageBox.critical(
                self, "Invalid URLs",
                "The following are not valid YouTube URLs:\n\n"
                + "\n".join(f"  {u}" for u in invalid)
            )
            return

        self._fetch_btn.setText("Fetching…")
        self._fetch_btn.setEnabled(False)
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

        from mdownloader.gui_qt.workers.metadata_fetch_worker import MetadataFetchWorker
        self._fetch_worker = MetadataFetchWorker(tasks, parent=self)
        self._fetch_worker.fetch_progress.connect(self._on_fetch_progress)
        self._fetch_worker.all_done.connect(self._on_fetch_done)
        self._fetch_worker.start()

    def _on_fetch_progress(self, current: int, total: int) -> None:
        if total > 1:
            self._fetch_btn.setText(f"Fetching… ({current}/{total})")
        else:
            self._fetch_btn.setText("Fetching…")

    def _on_fetch_done(self, tracks: list, errors: list) -> None:
        QApplication.restoreOverrideCursor()
        self._fetch_btn.setText("Get Track(s)")
        self._fetch_btn.setEnabled(True)

        if errors:
            details = "\n".join(f"  {url}\n    {msg}" for url, msg in errors)
            QMessageBox.critical(
                self, "Metadata Fetch Failed",
                "Could not fetch metadata for the following URLs:\n\n"
                + details
                + "\n\nCheck the URLs and your internet connection."
            )
            return

        self._tracks = [t for t in tracks if t is not None]
        self._populate_table()
        self._stack.setCurrentIndex(1)

    def _on_confirm(self) -> None:
        if not self._tracks:
            return

        # Sync any user-edited titles back into self._tracks
        for i in range(self._table.rowCount()):
            item = self._table.item(i, _COL_TITLE)
            if item:
                self._tracks[i]["track_title"] = item.text().strip() or self._tracks[i]["track_title"]

        count = len(self._tracks)
        reply = QMessageBox.question(
            self, "Confirm Download",
            f"Ready to download {count} track{'s' if count != 1 else ''}.\n\nProceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        config = load_config()
        root = config["download_root_dir"]

        # Output dir: playlist name > single artist > Mixed
        playlist_names = {t["album_name"] for t in self._tracks if t["album_name"] != "Singles"}
        artists = {t["artist_name"] for t in self._tracks}
        if len(playlist_names) == 1:
            folder = clean_filename(next(iter(playlist_names)))
        elif len(playlist_names) > 1:
            folder = "Mixed Playlists"
        elif len(artists) == 1:
            folder = clean_filename(next(iter(artists)))
        else:
            folder = "Mixed"

        from pathlib import Path
        self._output_dir = Path(root).expanduser() / "Singles" / folder

        self._download_total = count
        self._download_progress = 0
        self._download_btn.setText(f"Downloading 0/{count}")
        self._set_controls_enabled(False)

        from mdownloader.gui_qt.workers.album_download_worker import AlbumDownloadWorker
        tasks = [(i, t, t["youtube_url"]) for i, t in enumerate(self._tracks)]
        self._worker = AlbumDownloadWorker(
            tasks=tasks,
            output_dir=self._output_dir,
            parent=self,
        )
        self._worker.track_started.connect(self._on_track_started)
        self._worker.track_done.connect(self._on_track_done)
        self._worker.track_failed.connect(self._on_track_failed)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()

    def _set_controls_enabled(self, enabled: bool) -> None:
        self._table_back_btn.setEnabled(enabled)
        self._table_home_btn.setEnabled(enabled)
        self._download_btn.setEnabled(enabled)

    def _set_row_status(self, row: int, status: str, color: str) -> None:
        item = self._table.item(row, _COL_STATUS)
        if item:
            item.setText(status)
            item.setForeground(QColor(color))

    def _on_track_started(self, row: int) -> None:
        self._set_row_status(row, _STATUS_DOWNLOADING, "#ffaa00")

    def _on_track_done(self, row: int) -> None:
        self._set_row_status(row, _STATUS_DONE, ACCENT)
        self._download_progress += 1
        self._download_btn.setText(f"Downloading {self._download_progress}/{self._download_total}")

    def _on_track_failed(self, row: int, _error_msg: str) -> None:
        self._set_row_status(row, _STATUS_FAILED, "#ff4444")
        self._download_progress += 1
        self._download_btn.setText(f"Downloading {self._download_progress}/{self._download_total}")

    def _on_all_done(self, success: int, fail: int) -> None:
        self._set_controls_enabled(True)
        self._download_btn.setText("Confirm & Download")

        msg_box = QMessageBox(self)

        if fail == 0:
            msg_box.setWindowTitle("✓ Download Complete")
            msg_box.setText(
                f"All {success} track{'s' if success != 1 else ''} downloaded successfully.\n\n"
                f"Saved to:\n{self._output_dir}"
            )
            msg_box.setIcon(QMessageBox.Icon.Information)
        else:
            msg_box.setWindowTitle("✗ Download Incomplete")
            msg_box.setText(
                f"{fail} track{'s' if fail != 1 else ''} failed to download.\n"
                f"{success} track{'s' if success != 1 else ''} succeeded.\n\n"
                f"Failed tracks are shown in red in the table.\n\n"
                f"Saved to:\n{self._output_dir}"
            )
            msg_box.setIcon(QMessageBox.Icon.Warning)

        open_btn = msg_box.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
        msg_box.addButton("Close", QMessageBox.ButtonRole.RejectRole)
        msg_box.exec()

        if msg_box.clickedButton() == open_btn and self._output_dir:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(["open", str(self._output_dir)])

        if fail == 0:
            self.close()
