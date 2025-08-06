"""Utility functions shared across the music downloader scripts.

This module centralizes small helper functions that would otherwise be
duplicated across multiple scripts. Importing from a single utils module
simplifies maintenance and reduces the risk of inconsistencies.
"""

import os
import re
from pathlib import Path
from datetime import timedelta

def get_tmp_dir(test_mode: bool) -> Path:
    """Return the appropriate temporary directory path.

    Args:
        test_mode: If True, return the test-mode temp directory; otherwise
            return the dry-run directory.

    Returns:
        pathlib.Path pointing to the temp directory.
    """
    return Path("/tmp/music_downloader_test") if test_mode else Path("/tmp/music_downloader_dryrun")


def seconds_to_mmss(seconds: int) -> str:
    """Convert a duration in seconds to MM:SS format.

    Args:
        seconds: Duration in seconds.

    Returns:
        A string formatted as minutes:seconds, or an empty string if the input
        is falsy.
    """
    if not seconds:
        return ""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"


def parse_duration_str(duration_str: str):
    """Parse a duration string of the form MM:SS into seconds.

    Returns None for invalid inputs.
    """
    try:
        minutes, seconds = map(int, duration_str.strip().split(":"))
        return timedelta(minutes=minutes, seconds=seconds).total_seconds()
    except Exception:
        return None


def clean_filename(text: str) -> str:
    """Sanitize a string for use as a filename.

    Allows alphanumeric characters, spaces, hyphens, underscores, parentheses
    and periods. Leading/trailing whitespace is stripped.
    """
    allowed = set(" -_().")
    return "".join(c for c in text if c.isalnum() or c in allowed).strip()


def clean_youtube_url(original_url: str) -> str:
    """Extract a canonical YouTube watch URL from various URL formats.

    This helper parses a YouTube URL and returns a simplified
    "https://www.youtube.com/watch?v=VIDEO_ID" string when possible. If the
    video ID cannot be determined, the original URL is returned unchanged.
    """
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(original_url)
    query = parse_qs(parsed.query)
    video_id = query.get("v", [None])[0]
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return original_url


def clean_track_title(title: str) -> str:
    """Normalize track titles by removing boilerplate and formatting featured artists.

    This helper performs several operations to produce a clean, human‑friendly
    track title:

      * Removes common boilerplate phrases like "Official Video", "Official Audio",
        or "Lyrics" regardless of case.
      * Strips out any bracketed segments (e.g., "[Official Video]"), which are
        often used for quality tags or video descriptors.
      * Removes leftover empty parentheses or brackets that may result from
        stripping descriptors.
      * Normalizes any "feat" or "featuring" clauses into a single
        "(feat. X)" suffix. The original "feat" segment is removed wherever
        it appears in the title, whether inside or outside of parentheses.
      * Collapses multiple consecutive whitespace characters into a single
        space and trims stray hyphens at the edges.

    Args:
        title: The raw track title string extracted from a YouTube video.

    Returns:
        A cleaned track title string suitable for display and filename usage.
    """
    if not title:
        return title

    # Remove explicit phrases regardless of location (case-insensitive)
    for term in ["Official Video", "Official Audio", "Lyrics", "Lyric Video", "Audio"]:
        title = re.sub(rf"\b{re.escape(term)}\b", "", title, flags=re.IGNORECASE)

    # Remove any bracketed segments entirely (e.g., [Official Video], [HD])
    title = re.sub(r"\[[^\]]*\]", "", title)

    # Remove empty parentheses or brackets left after stripping
    title = re.sub(r"\(\s*\)", "", title)
    title = re.sub(r"\[\s*\]", "", title)

    # Normalize 'feat' clauses. First handle cases where 'feat' appears in
    # parentheses, e.g. "(feat. Artist)". Extract the artist name and remove the
    # entire segment. We'll append it back at the end.
    featured = None
    # Match '(feat ...)' ignoring case
    feat_paren = re.search(r"\(\s*feat(?:uring)?\.?(.*?)\)", title, flags=re.IGNORECASE)
    if feat_paren:
        featured = feat_paren.group(1).strip()
        # Remove the entire '(feat...)' segment
        title = feat_paren.re.sub("", title).strip()
    else:
        # Match 'feat. Artist' outside of parentheses
        feat_inline = re.search(r"feat(?:uring)?\.?(.*)", title, flags=re.IGNORECASE)
        if feat_inline:
            featured = feat_inline.group(1).strip()
            # Remove the 'feat...' portion from the title
            title = feat_inline.re.sub("", title).strip()

    # Collapse multiple spaces into one
    title = " ".join(title.split())

    # Trim stray hyphens and whitespace at the ends
    title = title.strip(" -")

    # Append the normalized '(feat. ...)' if we captured a featured artist
    if featured:
        # Ensure there isn't already a trailing parenthesis before adding
        title = f"{title} (feat. {featured})" if title else f"(feat. {featured})"

    return title