"""Album download workflow: URL input → track table → confirm & download."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableView, QHeaderView, QFrame, QMessageBox, QAbstractItemView,
    QStackedWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QCursor

from mdownloader.config import load_config
from mdownloader.core.utils import detect_source_type, clean_filename
from mdownloader.gui_qt.models.track_table_model import TrackTableModel


class AlbumFlowWindow(QWidget):
    """Two-screen flow: URL input → editable track table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model: TrackTableModel | None = None
        self._album_name = ""
        self._artist_name = ""
        self._output_dir = None
        self._worker = None
        self._playlist_worker = None
        self._download_total = 0
        self._download_progress = 0
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Music Downloader — Album")
        self.setMinimumSize(QSize(780, 520))

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setLayout(root_layout)

        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack)

        self._stack.addWidget(self._build_url_screen())    # index 0
        self._stack.addWidget(self._build_table_screen())  # index 1
        self._stack.setCurrentIndex(0)

    # ── Screen 0: URL input ───────────────────────────────────────────────────

    def _build_url_screen(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(0)
        page.setLayout(layout)

        title = QLabel("Download Album")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        layout.addSpacing(8)

        subtitle = QLabel(
            "Paste an Apple Music or Wikipedia album URL below.\n"
            "The app will fetch the track list automatically."
        )
        subtitle.setObjectName("appSubtitle")
        layout.addWidget(subtitle)

        layout.addSpacing(28)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        layout.addSpacing(28)

        url_label = QLabel("ALBUM URL")
        url_label.setObjectName("sectionLabel")
        layout.addWidget(url_label)

        layout.addSpacing(10)

        self._url_input = QLineEdit()
        self._url_input.setObjectName("urlInput")
        self._url_input.setPlaceholderText(
            "https://music.apple.com/…  or  https://en.wikipedia.org/wiki/…"
        )
        self._url_input.setFixedHeight(40)
        self._url_input.returnPressed.connect(self._on_parse)
        layout.addWidget(self._url_input)

        layout.addSpacing(20)

        self._parse_btn = QPushButton("Fetch Track List")
        self._parse_btn.setObjectName("primaryBtn")
        self._parse_btn.setFixedHeight(48)
        self._parse_btn.clicked.connect(self._on_parse)
        layout.addWidget(self._parse_btn)

        layout.addStretch()

        # Back to home
        back_btn = QPushButton("← Back to Home")
        back_btn.setObjectName("linkBtn")
        back_btn.setFixedHeight(28)
        back_btn.clicked.connect(self.close)
        layout.addWidget(back_btn)

        return page

    # ── Screen 1: Track table ─────────────────────────────────────────────────

    def _build_table_screen(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(0)
        page.setLayout(layout)

        # Album info header
        self._album_label = QLabel()
        self._album_label.setObjectName("appTitle")
        layout.addWidget(self._album_label)

        layout.addSpacing(4)

        self._artist_label = QLabel()
        self._artist_label.setObjectName("appSubtitle")
        layout.addWidget(self._artist_label)

        layout.addSpacing(12)

        instructions = QLabel(
            "Paste a YouTube URL into the  YouTube URL  column for each track you want to download. "
            "Rows with no URL will be skipped."
        )
        instructions.setObjectName("folderPath")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        layout.addSpacing(16)

        # ── YouTube playlist auto-fill ────────────────────────────────────────
        playlist_label = QLabel("YOUTUBE PLAYLIST  (optional auto-fill)")
        playlist_label.setObjectName("sectionLabel")
        layout.addWidget(playlist_label)

        layout.addSpacing(8)

        playlist_row = QHBoxLayout()
        playlist_row.setSpacing(10)

        self._playlist_input = QLineEdit()
        self._playlist_input.setObjectName("urlInput")
        self._playlist_input.setPlaceholderText(
            "https://www.youtube.com/playlist?list=…"
        )
        self._playlist_input.setFixedHeight(36)
        self._playlist_input.returnPressed.connect(self._on_autofill)
        playlist_row.addWidget(self._playlist_input)

        self._autofill_btn = QPushButton("Auto-fill")
        self._autofill_btn.setObjectName("secondaryBtn")
        self._autofill_btn.setFixedHeight(36)
        self._autofill_btn.setFixedWidth(100)
        self._autofill_btn.clicked.connect(self._on_autofill)
        playlist_row.addWidget(self._autofill_btn)

        layout.addLayout(playlist_row)

        layout.addSpacing(16)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        layout.addSpacing(12)

        # Table
        self._table_view = QTableView()
        self._table_view.setObjectName("trackTable")
        self._table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_view.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked |
            QAbstractItemView.EditTrigger.SelectedClicked |
            QAbstractItemView.EditTrigger.AnyKeyPressed
        )
        self._table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table_view.verticalHeader().setVisible(False)
        self._table_view.setShowGrid(True)
        self._table_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._table_view)

        layout.addSpacing(12)

        # URL count label
        self._url_count_label = QLabel("0 of 0 tracks have a YouTube URL")
        self._url_count_label.setObjectName("folderPath")
        layout.addWidget(self._url_count_label)

        layout.addSpacing(12)

        sep2 = QFrame()
        sep2.setObjectName("separator")
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        layout.addSpacing(16)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._back_btn = QPushButton("← Back")
        self._back_btn.setObjectName("secondaryBtn")
        self._back_btn.setFixedHeight(42)
        self._back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        btn_row.addWidget(self._back_btn)

        self._home_btn = QPushButton("Return to Home")
        self._home_btn.setObjectName("secondaryBtn")
        self._home_btn.setFixedHeight(42)
        self._home_btn.clicked.connect(self.close)
        btn_row.addWidget(self._home_btn)

        btn_row.addStretch()

        self._confirm_btn = QPushButton("Confirm & Download")
        self._confirm_btn.setObjectName("primaryBtn")
        self._confirm_btn.setFixedHeight(42)
        self._confirm_btn.clicked.connect(self._on_confirm)
        btn_row.addWidget(self._confirm_btn)

        layout.addLayout(btn_row)

        return page

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_parse(self):
        url = self._url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "No URL", "Please paste an album URL first.")
            return

        source = detect_source_type(url)
        if source == "unknown":
            QMessageBox.critical(
                self, "Unsupported URL",
                "Only Apple Music (music.apple.com) and Wikipedia (en.wikipedia.org) "
                "album URLs are supported.\n\nPlease check your URL and try again."
            )
            return

        # Show loading state
        self._parse_btn.setText("Fetching…")
        self._parse_btn.setEnabled(False)
        self._url_input.setEnabled(False)
        from PyQt6.QtWidgets import QApplication
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        QApplication.processEvents()

        try:
            if source == "apple":
                from mdownloader.parsers.apple import parse_apple_album
                album_name, artist_name, tracks = parse_apple_album(url)
            else:
                from mdownloader.parsers.wiki import parse_wiki_album
                album_name, artist_name, tracks = parse_wiki_album(url)
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self._parse_btn.setText("Fetch Track List")
            self._parse_btn.setEnabled(True)
            self._url_input.setEnabled(True)
            QMessageBox.critical(
                self, "Parse Failed",
                f"Could not retrieve the track list.\n\n"
                f"Details:\n{exc}\n\n"
                f"Check the URL and your internet connection, then try again."
            )
            return

        QApplication.restoreOverrideCursor()
        self._parse_btn.setText("Fetch Track List")
        self._parse_btn.setEnabled(True)
        self._url_input.setEnabled(True)

        self._load_table(album_name, artist_name, tracks)
        self._stack.setCurrentIndex(1)

    def _load_table(self, album_name: str, artist_name: str, tracks: list[dict]):
        self._album_name = album_name
        self._artist_name = artist_name

        self._album_label.setText(album_name)
        self._artist_label.setText(artist_name)

        self._model = TrackTableModel(tracks, parent=self)
        self._model.dataChanged.connect(self._refresh_url_count)
        self._table_view.setModel(self._model)

        # Column widths
        hdr = self._table_view.horizontalHeader()
        hdr.resizeSection(0, 48)   # Disc
        hdr.resizeSection(1, 52)   # Track
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)   # Title
        hdr.resizeSection(3, 72)   # Duration
        hdr.resizeSection(4, 260)  # YouTube URL
        hdr.resizeSection(5, 100)  # Status

        self._refresh_url_count()

    def _refresh_url_count(self):
        if self._model:
            entered = self._model.url_count()
            total = self._model.rowCount()
            self._url_count_label.setText(
                f"{entered} of {total} tracks have a YouTube URL"
            )

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable navigation controls during download."""
        self._back_btn.setEnabled(enabled)
        self._home_btn.setEnabled(enabled)
        self._confirm_btn.setEnabled(enabled)
        self._autofill_btn.setEnabled(enabled)
        self._playlist_input.setEnabled(enabled)

    # ── Download signal handlers ───────────────────────────────────────────

    def _on_track_started(self, row: int) -> None:
        from mdownloader.gui_qt.models.track_table_model import STATUS_DOWNLOADING
        self._model.set_track_status(row, STATUS_DOWNLOADING)

    def _on_track_done(self, row: int) -> None:
        from mdownloader.gui_qt.models.track_table_model import STATUS_DONE
        self._model.set_track_status(row, STATUS_DONE)
        self._download_progress += 1
        self._confirm_btn.setText(f"Downloading {self._download_progress}/{self._download_total}")

    def _on_track_failed(self, row: int, error_msg: str) -> None:
        from mdownloader.gui_qt.models.track_table_model import STATUS_FAILED
        self._model.set_track_status(row, STATUS_FAILED)
        self._download_progress += 1
        self._confirm_btn.setText(f"Downloading {self._download_progress}/{self._download_total}")

    def _on_all_done(self, success: int, fail: int) -> None:
        self._confirm_btn.setText("Confirm && Download")
        self._confirm_btn.setStyleSheet("")
        self._set_controls_enabled(True)

        import subprocess
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

    def _on_autofill(self):
        if not self._model:
            return

        playlist_url = self._playlist_input.text().strip()
        if not playlist_url:
            QMessageBox.warning(
                self, "No Playlist URL",
                "Please paste a YouTube playlist URL first."
            )
            return

        self._autofill_btn.setText("Fetching…")
        self._autofill_btn.setEnabled(False)
        self._playlist_input.setEnabled(False)

        from mdownloader.gui_qt.workers.playlist_fetch_worker import PlaylistFetchWorker
        self._playlist_worker = PlaylistFetchWorker(playlist_url, parent=self)
        self._playlist_worker.finished.connect(self._on_autofill_done)
        self._playlist_worker.error.connect(self._on_autofill_error)
        self._playlist_worker.start()

    def _on_autofill_done(self, entries: list) -> None:
        self._autofill_btn.setText("Auto-fill")
        self._autofill_btn.setEnabled(True)
        self._playlist_input.setEnabled(True)

        if not entries:
            QMessageBox.warning(
                self, "Empty Playlist",
                "No tracks were found in that playlist. "
                "Check the URL and make sure the playlist is public."
            )
            return

        from mdownloader.services.playlist_matcher import match_playlist_to_tracks
        assignments = match_playlist_to_tracks(
            self._model._tracks, entries
        )

        # Only fill rows that are currently blank
        filled = 0
        for row, url in assignments.items():
            if not self._model.get_url(row).strip():
                self._model.set_track_url(row, url)
                filled += 1

        skipped_existing = len(assignments) - filled
        unmatched = self._model.rowCount() - len(assignments)

        parts = [f"Auto-filled {filled} of {self._model.rowCount()} tracks."]
        if unmatched:
            parts.append(f"{unmatched} had no close match.")
        if skipped_existing:
            parts.append(f"{skipped_existing} already had a URL and were left unchanged.")

        QMessageBox.information(self, "Auto-fill Complete", " ".join(parts))

    def _on_autofill_error(self, message: str) -> None:
        self._autofill_btn.setText("Auto-fill")
        self._autofill_btn.setEnabled(True)
        self._playlist_input.setEnabled(True)

        QMessageBox.critical(
            self, "Playlist Fetch Failed",
            f"Could not fetch the YouTube playlist.\n\n"
            f"Details:\n{message}\n\n"
            f"Check the URL and your internet connection, then try again."
        )

    def _on_confirm(self):
        if not self._model:
            return

        # Block if no URLs entered
        if self._model.url_count() == 0:
            QMessageBox.warning(
                self, "No URLs Entered",
                "You haven't entered any YouTube URLs yet.\n\n"
                "Paste at least one URL into the YouTube URL column to proceed."
            )
            return

        # Block if any non-blank URLs are invalid
        bad = self._model.invalid_urls()
        if bad:
            details = "\n".join(
                f"  Row {row + 1}: {url}" for row, url in bad
            )
            QMessageBox.critical(
                self, "Invalid YouTube URLs",
                f"The following URLs are not valid YouTube links. "
                f"Please correct or clear them before proceeding.\n\n{details}"
            )
            return

        # Confirm dialog
        entered = self._model.url_count()
        total = self._model.rowCount()
        skipped = total - entered
        msg = (
            f"Ready to download {entered} track{'s' if entered != 1 else ''}."
        )
        if skipped:
            msg += f"\n{skipped} row{'s' if skipped != 1 else ''} with no URL will be skipped."
        msg += "\n\nProceed?"

        reply = QMessageBox.question(
            self, "Confirm Download", msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Build output directory: <download_root>/<Artist> - <Album>/
        config = load_config()
        root = config["download_root_dir"]
        folder_name = clean_filename(f"{self._artist_name} - {self._album_name}")
        from pathlib import Path
        self._output_dir = Path(root).expanduser() / folder_name

        # Mark skipped rows immediately
        from mdownloader.gui_qt.models.track_table_model import (
            STATUS_SKIPPED, STATUS_PENDING,
        )
        for i in range(self._model.rowCount()):
            if not self._model.get_url(i).strip():
                self._model.set_track_status(i, STATUS_SKIPPED)
            else:
                self._model.set_track_status(i, STATUS_PENDING)

        self._download_total = entered
        self._download_progress = 0
        self._confirm_btn.setText(f"Downloading 0/{entered}")
        self._confirm_btn.setStyleSheet(
            "QPushButton { color: #ffaa00; border: 2px solid #ffaa00; "
            "background-color: transparent; border-radius: 6px; "
            "font-size: 15px; font-weight: 600; padding: 6px 20px; }"
        )
        self._set_controls_enabled(False)

        from mdownloader.gui_qt.workers.album_download_worker import AlbumDownloadWorker
        self._worker = AlbumDownloadWorker(
            tasks=self._model.rows_with_urls(),
            output_dir=self._output_dir,
            parent=self,
        )
        self._worker.track_started.connect(self._on_track_started)
        self._worker.track_done.connect(self._on_track_done)
        self._worker.track_failed.connect(self._on_track_failed)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.start()
