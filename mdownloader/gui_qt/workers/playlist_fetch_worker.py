"""Background worker: fetch YouTube playlist metadata via yt-dlp."""

from PyQt6.QtCore import QThread, pyqtSignal

import yt_dlp


class PlaylistFetchWorker(QThread):
    """Fetch a YouTube playlist's track list without downloading any media.

    Emits:
        finished(list[dict]): list of {title, url} dicts on success.
        error(str):           human-readable error message on failure.
    """

    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, playlist_url: str, parent=None):
        super().__init__(parent)
        self._url = playlist_url

    def run(self):
        try:
            opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self._url, download=False)

            entries = []
            for e in info.get("entries") or []:
                title = e.get("title", "").strip()
                video_id = e.get("id", "")
                if title and video_id:
                    entries.append({
                        "title": title,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                    })

            self.finished.emit(entries)
        except Exception as exc:
            self.error.emit(str(exc))
