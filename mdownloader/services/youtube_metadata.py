"""YouTube metadata extractor for individual track links.

Fetches title, artist, and duration from a YouTube URL using yt-dlp's
metadata-only mode.  No download, no file I/O — raises exceptions on
failure; callers handle error display.
"""

from __future__ import annotations

import yt_dlp

from mdownloader.core.utils import clean_track_title, seconds_to_mmss

PLAYLIST_TRACK_LIMIT = 50


def fetch_track_metadata(url: str) -> dict:
    """Extract track metadata from a YouTube URL using yt-dlp.

    Does a metadata-only fetch (no download).  Attempts a best-effort
    split on "Artist - Title" patterns in the video title; falls back
    to the channel/uploader name as the artist.

    Args:
        url: A YouTube watch URL.

    Returns:
        Dict with keys: track_title, artist_name, album_name,
        track_number, disc_number, track_duration, youtube_url.

    Raises:
        RuntimeError: If yt-dlp fails to fetch metadata.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,   # ignore list=/start_radio= params; fetch single video only
        # Use android client for consistency with downloader (avoids PO token issues)
        "extractor_args": {"youtube": {"player_client": ["android"]}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise RuntimeError(f"Could not fetch metadata: {exc}") from exc

    raw_title = info.get("title") or ""
    uploader = info.get("uploader") or info.get("channel") or "Unknown Artist"
    duration_secs = info.get("duration") or 0

    # Best-effort "Artist - Title" split on the first " - "
    if " - " in raw_title:
        parts = raw_title.split(" - ", 1)
        artist = parts[0].strip()
        track_title = clean_track_title(parts[1].strip())
    else:
        artist = uploader
        track_title = clean_track_title(raw_title)

    return {
        "track_title": track_title,
        "artist_name": artist,
        "album_name": "Singles",
        "track_number": "",
        "disc_number": 1,
        "track_duration": seconds_to_mmss(duration_secs),
        "youtube_url": url,
    }


def fetch_playlist_metadata(
    url: str,
    limit: int = PLAYLIST_TRACK_LIMIT,
) -> tuple[str, list[dict]]:
    """Extract metadata for all tracks in a YouTube playlist (up to limit).

    Uses extract_flat mode for speed — fetches the playlist index in one
    request rather than loading each video's page individually.

    Args:
        url:   A YouTube playlist URL (must contain list= parameter).
        limit: Maximum number of tracks to return (default PLAYLIST_TRACK_LIMIT).

    Returns:
        Tuple of (playlist_title, tracks) where tracks is a list of dicts
        with the same shape as fetch_track_metadata.

    Raises:
        RuntimeError: If yt-dlp fails or no entries are found.
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": "in_playlist",  # fast: one request for the full index
        "extractor_args": {"youtube": {"player_client": ["android"]}},
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise RuntimeError(f"Could not fetch playlist: {exc}") from exc

    playlist_title = info.get("title") or "Playlist"
    entries = info.get("entries") or []

    if not entries:
        raise RuntimeError(
            "No tracks found at this URL. "
            "Make sure it is a YouTube playlist URL and try again."
        )

    tracks: list[dict] = []
    for i, entry in enumerate(entries):
        if i >= limit:
            break
        if not entry:
            continue

        video_id = entry.get("id") or ""
        if not video_id:
            continue
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        raw_title = entry.get("title") or ""
        uploader = entry.get("uploader") or entry.get("channel") or "Unknown Artist"
        duration_secs = entry.get("duration") or 0

        if " - " in raw_title:
            parts = raw_title.split(" - ", 1)
            artist = parts[0].strip()
            track_title = clean_track_title(parts[1].strip())
        else:
            artist = uploader
            track_title = clean_track_title(raw_title)

        tracks.append({
            "track_title": track_title,
            "artist_name": artist,
            "album_name": playlist_title,
            "track_number": str(i + 1),
            "disc_number": 1,
            "track_duration": seconds_to_mmss(duration_secs),
            "youtube_url": video_url,
        })

    if not tracks:
        raise RuntimeError("No valid tracks could be read from this playlist.")

    return playlist_title, tracks
