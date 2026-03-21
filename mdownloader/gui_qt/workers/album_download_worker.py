"""Background QThread worker for sequential album track downloads."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from mdownloader.services.downloader import download_track


class AlbumDownloadWorker(QThread):
    """Downloads a list of tracks sequentially in a background thread.

    Signals:
        track_started(row_index)            — emitted just before a track starts
        track_done(row_index)               — emitted on successful download
        track_failed(row_index, error_msg)  — emitted on failure
        all_done(success_count, fail_count) — emitted when all tracks finish
    """

    track_started = pyqtSignal(int)
    track_done = pyqtSignal(int)
    track_failed = pyqtSignal(int, str)
    all_done = pyqtSignal(int, int)

    def __init__(
        self,
        tasks: list[tuple[int, dict, str]],   # (row_index, track_dict, url)
        output_dir: Path,
        parent=None,
    ):
        super().__init__(parent)
        self._tasks = tasks
        self._output_dir = output_dir

    def run(self) -> None:
        success = 0
        fail = 0
        for row_idx, track, url in self._tasks:
            self.track_started.emit(row_idx)
            try:
                download_track(track, url, self._output_dir)
                self.track_done.emit(row_idx)
                success += 1
            except Exception as exc:
                self.track_failed.emit(row_idx, str(exc))
                fail += 1
        self.all_done.emit(success, fail)
