"""Background QThread worker for fetching YouTube track metadata."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from mdownloader.services.youtube_metadata import fetch_track_metadata, fetch_playlist_metadata


class MetadataFetchWorker(QThread):
    """Fetches yt-dlp metadata for a list of (url, is_playlist) tasks.

    Signals:
        fetch_progress(current, total)  — emitted before each task starts
        track_ready(index, track_dict)  — emitted after each successful single fetch
        track_error(index, url, msg)    — emitted on failure for a task
        all_done(tracks, errors)        — emitted when all tasks are processed
            tracks: flat list of track dicts (None for failed tasks)
            errors: list of (url, error_message) for failures
    """

    fetch_progress = pyqtSignal(int, int)   # (current_task, total_tasks)
    track_ready = pyqtSignal(int, dict)
    track_error = pyqtSignal(int, str, str)
    all_done = pyqtSignal(list, list)

    def __init__(self, tasks: list[tuple[str, bool]], parent=None):
        """
        Args:
            tasks: List of (url, is_playlist) tuples.
        """
        super().__init__(parent)
        self._tasks = tasks

    def run(self) -> None:
        tracks: list[dict | None] = []
        errors: list[tuple[str, str]] = []
        total = len(self._tasks)

        for i, (url, is_playlist) in enumerate(self._tasks):
            self.fetch_progress.emit(i + 1, total)
            try:
                if is_playlist:
                    _, playlist_tracks = fetch_playlist_metadata(url)
                    for track in playlist_tracks:
                        tracks.append(track)
                        self.track_ready.emit(len(tracks) - 1, track)
                else:
                    track = fetch_track_metadata(url)
                    tracks.append(track)
                    self.track_ready.emit(len(tracks) - 1, track)
            except Exception as exc:
                tracks.append(None)
                errors.append((url, str(exc)))
                self.track_error.emit(i, url, str(exc))

        self.all_done.emit(tracks, errors)
