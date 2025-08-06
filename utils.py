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

    Removes phrases like "Official Video" or "Official Audio", normalizes
    "feat"/"featuring" patterns into "(feat. X)", collapses extra spaces and
    trims stray hyphens.
    """
    if not title:
        return title
    # Remove common boilerplate terms (case-insensitive)
    title = re.sub(r"\bOfficial\s+Video\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\bOfficial\s+Audio\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\bLyrics?\b", "", title, flags=re.IGNORECASE)
    # Normalize 'feat' into parentheses
    feat_match = re.search(r"feat\.?\s+([^()\-]+)", title, flags=re.IGNORECASE)
    if feat_match:
        featured = feat_match.group(1).strip()
        title = re.sub(r"feat\.?\s+" + re.escape(featured), "", title, flags=re.IGNORECASE).strip()
        title = f"{title.strip()} (feat. {featured})"
    # Collapse whitespace and trim stray hyphens
    title = " ".join(title.split())
    title = title.strip("- ")
    return title