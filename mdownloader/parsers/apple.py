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

# Storefronts to try if the primary country returns no tracks
_FALLBACK_COUNTRIES = ["us", "gb", "fr", "de", "jp", "au", "ca"]


def clean_apple_url(url: str) -> str:
    """Strip query parameters and fragments from an Apple Music URL."""
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))


def extract_album_id(url: str) -> str | None:
    """Extract the numeric album ID from an Apple Music URL."""
    match = re.search(r"/album/.*?/(\d+)", url)
    return match.group(1) if match else None


def extract_country_code(url: str) -> str | None:
    """Extract the two-letter country code from an Apple Music URL.

    Handles URLs of the form: music.apple.com/{country}/album/...
    Returns None if no country segment is found.
    """
    match = re.search(r"music\.apple\.com/([a-z]{2})/", url)
    return match.group(1) if match else None


def _fetch_tracks(album_id: str, country: str) -> tuple[str, str, list[dict]] | None:
    """Query the iTunes API for a specific album ID and country storefront.

    Returns (album_name, artist_name, tracks) if tracks are found, else None.
    Raises RuntimeError on network / HTTP errors.
    """
    api_url = (
        f"https://itunes.apple.com/lookup?id={album_id}&entity=song&country={country}"
    )
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
    if not results or len(results) < 2:
        return None

    album_meta = results[0]
    album_name = album_meta.get("collectionName", "Unknown Album")
    artist_name = album_meta.get("artistName", "Unknown Artist")

    raw_tracks = [
        (item.get("discNumber", 1), item.get("trackNumber", 0), item)
        for item in results[1:]
        if item.get("wrapperType") == "track"
    ]
    if not raw_tracks:
        return None

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

    return (album_name, artist_name, tracks) if tracks else None


def parse_apple_album(url: str) -> tuple[str, str, list[dict]]:
    """Fetch album track data from the iTunes Lookup API.

    Tries the storefront country extracted from the URL first, then falls back
    through a list of common storefronts if the primary returns no tracks.

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

    # Build ordered list of countries to try: URL country first, then fallbacks
    primary = extract_country_code(url)
    countries = ([primary] if primary else []) + [
        c for c in _FALLBACK_COUNTRIES if c != primary
    ]

    result = None
    for country in countries:
        result = _fetch_tracks(album_id, country)
        if result is not None:
            break

    if result is None:
        raise RuntimeError(
            f"Apple API returned no tracks for this album in any storefront: {url}"
        )

    album_name, artist_name, tracks = result
    return album_name, artist_name, tracks
