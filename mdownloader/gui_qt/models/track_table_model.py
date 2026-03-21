"""Qt table model for the track list editor."""

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

from mdownloader.core.utils import is_valid_youtube_url

# Column indices
COL_DISC = 0
COL_TRACK = 1
COL_TITLE = 2
COL_DURATION = 3
COL_URL = 4
COL_STATUS = 5

HEADERS = ["Disc", "Track", "Title", "Duration", "YouTube URL", "Status"]

# Status values
STATUS_PENDING = "Pending"
STATUS_DOWNLOADING = "Downloading"
STATUS_DONE = "Downloaded"
STATUS_FAILED = "Failed"
STATUS_SKIPPED = "Skipped"


class TrackTableModel(QAbstractTableModel):
    """Model backing the album track table.

    Read-only columns: Disc, Track, Title, Duration, Status.
    Editable column: YouTube URL.
    """

    def __init__(self, tracks: list[dict], parent=None):
        super().__init__(parent)
        self._tracks = tracks                      # list of track dicts
        self._urls: list[str] = [""] * len(tracks) # user-entered YouTube URLs
        self._statuses: list[str] = [STATUS_PENDING] * len(tracks)

    # ── QAbstractTableModel interface ─────────────────────────────────────────

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._tracks)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(HEADERS)

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return HEADERS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        track = self._tracks[row]

        if role == Qt.ItemDataRole.DisplayRole:
            if col == COL_DISC:
                return str(track.get("disc_number", 1))
            if col == COL_TRACK:
                return str(track.get("track_number", ""))
            if col == COL_TITLE:
                return track.get("track_title", "")
            if col == COL_DURATION:
                return track.get("track_duration", "")
            if col == COL_URL:
                return self._urls[row]
            if col == COL_STATUS:
                return self._statuses[row]

        if role == Qt.ItemDataRole.ForegroundRole:
            from PyQt6.QtGui import QColor
            from mdownloader.gui_qt.style import ACCENT, TEXT_MUTED, TEXT_DIM
            if col == COL_STATUS:
                status = self._statuses[row]
                if status == STATUS_DONE:
                    return QColor(ACCENT)
                if status == STATUS_FAILED:
                    return QColor("#ff4444")
                if status == STATUS_DOWNLOADING:
                    return QColor("#ffaa00")
                return QColor(TEXT_MUTED)
            if col == COL_URL:
                url = self._urls[row]
                if url and not is_valid_youtube_url(url):
                    return QColor("#ff4444")   # red for invalid URL
                if url:
                    return QColor(ACCENT)
                return QColor(TEXT_DIM)

        if role == Qt.ItemDataRole.EditRole and col == COL_URL:
            return self._urls[row]

        return None

    def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if not index.isValid() or index.column() != COL_URL:
            return False
        if role == Qt.ItemDataRole.EditRole:
            self._urls[index.row()] = (value or "").strip()
            self.dataChanged.emit(index, index, [role, Qt.ItemDataRole.DisplayRole])
            return True
        return False

    def flags(self, index: QModelIndex):
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == COL_URL:
            return base | Qt.ItemFlag.ItemIsEditable
        return base

    # ── Public helpers ────────────────────────────────────────────────────────

    def set_track_status(self, row: int, status: str) -> None:
        """Update the status for a single row and notify the view."""
        self._statuses[row] = status
        idx = self.index(row, COL_STATUS)
        self.dataChanged.emit(idx, idx)

    def set_track_url(self, row: int, url: str) -> None:
        self._urls[row] = url.strip()
        idx = self.index(row, COL_URL)
        self.dataChanged.emit(idx, idx)

    def get_url(self, row: int) -> str:
        return self._urls[row]

    def url_count(self) -> int:
        """Number of rows with a non-blank URL."""
        return sum(1 for u in self._urls if u.strip())

    def invalid_urls(self) -> list[tuple[int, str]]:
        """Return list of (row_index, url) for non-blank, invalid URLs."""
        return [
            (i, u) for i, u in enumerate(self._urls)
            if u.strip() and not is_valid_youtube_url(u)
        ]

    def rows_with_urls(self) -> list[tuple[int, dict, str]]:
        """Return (row_index, track_dict, url) for every row that has a URL."""
        return [
            (i, self._tracks[i], self._urls[i])
            for i in range(len(self._tracks))
            if self._urls[i].strip()
        ]
