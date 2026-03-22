"""Utility functions shared across the music downloader."""

import re
import subprocess
import sys
from pathlib import Path
from datetime import timedelta


def open_folder(path: Path) -> None:
    """Open a folder in the system file manager (cross-platform)."""
    if sys.platform == "win32":
        subprocess.run(["explorer", str(path)])
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)])
    else:
        subprocess.run(["xdg-open", str(path)])


def get_tmp_dir(test_mode: bool) -> Path:
    """Return the appropriate temporary directory path."""
    import tempfile
    base = Path(tempfile.gettempdir())
    return base / ("music_downloader_test" if test_mode else "music_downloader_dryrun")


def seconds_to_mmss(seconds: int) -> str:
    """Convert a duration in seconds to MM:SS format."""
    if not seconds:
        return ""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"


def parse_duration_str(duration_str: str):
    """Parse a duration string of the form MM:SS into seconds. Returns None on failure."""
    try:
        minutes, seconds = map(int, duration_str.strip().split(":"))
        return timedelta(minutes=minutes, seconds=seconds).total_seconds()
    except Exception:
        return None


def clean_filename(text: str) -> str:
    """Sanitize a string for use as a filename."""
    allowed = set(" -_().")
    return "".join(c for c in text if c.isalnum() or c in allowed).strip()


def clean_youtube_url(original_url: str) -> str:
    """Extract a canonical YouTube watch URL from various URL formats."""
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(original_url)
    query = parse_qs(parsed.query)
    video_id = query.get("v", [None])[0]
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return original_url


def is_valid_youtube_url(url: str) -> bool:
    """Return True if the URL is a recognisable YouTube watch link."""
    from urllib.parse import urlparse
    if not url or not url.strip():
        return False
    try:
        p = urlparse(url.strip())
    except Exception:
        return False
    host = p.netloc.lower().removeprefix("www.")
    if host == "youtu.be":
        return bool(p.path.strip("/"))
    if host in ("youtube.com", "music.youtube.com"):
        from urllib.parse import parse_qs
        qs = parse_qs(p.query)
        return bool(qs.get("v") or qs.get("list"))  # accept watch URLs and playlist URLs
    return False


def detect_source_type(url: str) -> str:
    """Return 'apple', 'wiki', or 'unknown' based on URL domain."""
    from urllib.parse import urlparse
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if "music.apple.com" in host:
        return "apple"
    if "wikipedia.org" in host:
        return "wiki"
    return "unknown"


def clean_track_title(title: str) -> str:
    """Normalize a track title by removing boilerplate and standardizing featured artists."""
    if not title:
        return title

    for term in ["Official Video", "Official Audio", "Lyric Video", "Lyrics", "Audio"]:
        title = re.sub(rf"\b{re.escape(term)}\b", "", title, flags=re.IGNORECASE)

    title = re.sub(r"\[[^\]]*\]", "", title)
    title = re.sub(r"\(\s*\)", "", title)
    title = re.sub(r"\[\s*\]", "", title)

    featured = None
    feat_paren = re.search(r"\(\s*feat(?:uring)?\.?(.*?)\)", title, flags=re.IGNORECASE)
    if feat_paren:
        featured = feat_paren.group(1).strip()
        title = feat_paren.re.sub("", title).strip()
    else:
        feat_inline = re.search(r"feat(?:uring)?\.?(.*)", title, flags=re.IGNORECASE)
        if feat_inline:
            featured = feat_inline.group(1).strip()
            title = feat_inline.re.sub("", title).strip()

    title = " ".join(title.split()).strip(" -")

    if featured:
        title = f"{title} (feat. {featured})" if title else f"(feat. {featured})"

    return title
