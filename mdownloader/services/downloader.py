"""Single-track download and ID3 tag service.

Downloads a YouTube URL to MP3 using yt-dlp + ffmpeg, then writes
ID3 metadata tags using mutagen.  No GUI concerns — raises exceptions
on failure; callers decide how to report errors.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yt_dlp
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, ID3NoHeaderError

from mdownloader.core.utils import clean_filename


def _build_stem(track: dict) -> str:
    """Return the filename stem (no extension) for a track.

    Albums:  01 - Artist - Title  (or 1-01 - Artist - Title for multi-disc)
    Singles: Artist - Title  (no track number prefix when track_number is absent)
    """
    disc = int(track.get("disc_number") or 1)
    num_raw = track.get("track_number")
    artist = clean_filename(track.get("artist_name") or "Unknown")
    title = clean_filename(track.get("track_title") or "Unknown")
    if num_raw:
        num = int(num_raw)
        prefix = f"{disc}-{num:02d}" if disc > 1 else f"{num:02d}"
        return f"{prefix} - {artist} - {title}"
    return f"{artist} - {title}"


def download_track(track: dict, url: str, output_dir: Path) -> Path:
    """Download a YouTube URL as a 192 kbps MP3 and apply ID3 tags.

    Args:
        track: Track metadata dict with keys: disc_number, track_number,
               track_title, artist_name, album_name.
        url:   YouTube watch URL.
        output_dir: Directory to write the MP3 into (created if absent).

    Returns:
        Path to the saved .mp3 file.

    Raises:
        RuntimeError: On yt-dlp failure or missing output file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = _build_stem(track)
    mp3_path = output_dir / f"{stem}.mp3"

    # When frozen inside a .app, PATH is empty — point yt-dlp at the bundled
    # ffmpeg binary directly. Fall back to PATH lookup when running from source.
    if getattr(sys, "frozen", False):
        ffmpeg_dir = sys._MEIPASS
    else:
        ffmpeg_dir = shutil.which("ffmpeg")
        ffmpeg_dir = str(Path(ffmpeg_dir).parent) if ffmpeg_dir else None

    ydl_opts: dict = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": str(output_dir / stem),   # yt-dlp appends the real ext
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        # Use android client — avoids SABR (web) and GVS PO Token requirements
        # (ios, mweb).  android uses a different API path and remains the most
        # stable client for audio extraction without tokens.
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        **({"ffmpeg_location": ffmpeg_dir} if ffmpeg_dir else {}),
    }

    # Pass node/deno runtimes to yt-dlp if available (helps with some JS-heavy pages)
    js_runtimes: dict = {}
    if node := shutil.which("node"):
        js_runtimes["node"] = {"path": node}
    if deno := shutil.which("deno"):
        js_runtimes["deno"] = {"path": deno}
    if js_runtimes:
        ydl_opts["js_runtimes"] = js_runtimes

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:
        raise RuntimeError(f"Download failed: {exc}") from exc

    if not mp3_path.exists():
        raise RuntimeError(
            f"Expected output file not found after download: {mp3_path.name}\n"
            "Make sure ffmpeg is installed and accessible in your PATH."
        )

    _tag_mp3(mp3_path, track)
    return mp3_path


def _tag_mp3(mp3_path: Path, track: dict) -> None:
    """Write ID3 tags to an MP3 file using mutagen."""
    try:
        tags = ID3(str(mp3_path))
    except ID3NoHeaderError:
        tags = ID3()

    tags["TIT2"] = TIT2(encoding=3, text=track.get("track_title") or "")
    tags["TPE1"] = TPE1(encoding=3, text=track.get("artist_name") or "")
    tags["TALB"] = TALB(encoding=3, text=track.get("album_name") or "")

    track_num = track.get("track_number")
    if track_num:
        tags["TRCK"] = TRCK(encoding=3, text=str(track_num))

    tags.save(str(mp3_path))
