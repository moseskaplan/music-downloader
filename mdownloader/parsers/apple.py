"""Apple Music album parser.

Queries the public iTunes Lookup API to fetch track metadata for an album.
Returns a list of track dicts — no file I/O, no CLI concerns.
"""

from __future__ import annotations

import re
import time
from urllib.parse import urlparse, urlunparse

import requests

from mdownloader.core.utils import seconds_to_mmss


def clean_apple_url(url: str) -> str:
    """Strip query parameters and fragments from an Apple Music URL."""
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))


def extract_album_id(url: str) -> str | None:
    """Extract the numeric album ID from an Apple Music URL."""
    match = re.search(r"/album/.*?/(\d+)", url)
    return match.group(1) if match else None


def parse_apple_album(url: str) -> tuple[str, str, list[dict]]:
    """Fetch album track data from the iTunes Lookup API.

    Args:
        url: An Apple Music album URL.

    Returns:
        Tuple of (album_name, artist_name, tracks) where tracks is a list of
        dicts with keys: disc_number, track_number, track_title, artist_name,
        album_name, track_duration.

    Raises:
        ValueError: If the album ID cannot be extracted from the URL.
        RuntimeError: If the API request fails or returns no tracks.
    """
    url = clean_apple_url(url)
    album_id = extract_album_id(url)
    if not album_id:
        raise ValueError(f"Could not extract album ID from URL: {url}")

    api_url = f"https://itunes.apple.com/lookup?id={album_id}&entity=song"
    data = None
    for attempt in range(3):
        try:
            resp = requests.get(api_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            break
        except requests.exceptions.HTTPError:
            status = resp.status_code
            if status == 429 or 500 <= status < 600:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Apple API returned HTTP {status}")
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Apple API request failed: {exc}") from exc

    if data is None:
        raise RuntimeError("Apple API did not respond after 3 attempts.")

    results = data.get("results", [])
    if not results:
        raise RuntimeError("Apple API returned no results for this album.")

    album_meta = results[0]
    album_name = album_meta.get("collectionName", "Unknown Album")
    artist_name = album_meta.get("artistName", "Unknown Artist")

    if len(results) < 2:
        raise RuntimeError(
            f"Apple API returned album metadata but no tracks for: {url}"
        )

    # Sort tracks by disc then track number
    raw_tracks = [
        (item.get("discNumber", 1), item.get("trackNumber", 0), item)
        for item in results[1:]
        if item.get("wrapperType") == "track"
    ]
    raw_tracks.sort(key=lambda x: (x[0], x[1]))

    tracks: list[dict] = []
    for disc, num, item in raw_tracks:
        title = item.get("trackName")
        if not title:
            continue
        duration_secs = (item.get("trackTimeMillis") or 0) // 1000
        tracks.append({
            "disc_number": disc,
            "track_number": num,
            "track_title": title,
            "artist_name": item.get("artistName", artist_name),
            "album_name": album_name,
            "track_duration": seconds_to_mmss(duration_secs),
        })

    if not tracks:
        raise RuntimeError("No playable tracks found for this album.")

    return album_name, artist_name, tracks
