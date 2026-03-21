"""Wikipedia album parser.

Scrapes a Wikipedia album page to extract the track listing.
Returns a list of track dicts — no file I/O, no CLI concerns.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


def clean_wiki_url(url: str) -> str:
    """Remove query parameters and fragments from a Wikipedia URL."""
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, "", "", ""))


def _clean_album_title(raw: str) -> str:
    """Strip parenthetical descriptors from a page title."""
    return re.sub(r"\s*\(.*?\)\s*", "", raw).strip()


def parse_wiki_album(url: str) -> tuple[str, str, list[dict]]:
    """Scrape a Wikipedia album page and return track metadata.

    Args:
        url: A Wikipedia album page URL.

    Returns:
        Tuple of (album_name, artist_name, tracks) where tracks is a list of
        dicts with keys: disc_number, track_number, track_title, artist_name,
        album_name, track_duration.

    Raises:
        RuntimeError: If no tracklist table is found, or artist cannot be
            determined.
        requests.RequestException: On network failure.
    """
    url = clean_wiki_url(url)
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise RuntimeError(f"Could not fetch Wikipedia page: {exc}") from exc

    soup = BeautifulSoup(resp.content, "html.parser")

    # ── Find a tracklist table (must have both 'title' and 'length' headers) ─
    tracklist_table = None
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if "title" in headers and "length" in headers:
            tracklist_table = table
            break

    if tracklist_table is None:
        raise RuntimeError(
            "No track listing table found on this Wikipedia page. "
            "The page may use an unsupported layout."
        )

    # Handle tables nested inside the tracklist table
    nested = tracklist_table.find("table")
    row_source = nested if nested else tracklist_table
    track_rows = row_source.find_all("tr")[1:]  # skip header row

    # ── Album and artist name ─────────────────────────────────────────────────
    h1 = soup.find("h1")
    album_name = _clean_album_title(h1.get_text(strip=True)) if h1 else "Unknown Album"

    artist_name: str | None = None
    infobox = soup.find("table", class_="infobox")
    if infobox:
        for row in infobox.find_all("tr"):
            text = row.get_text()
            if "by" in text.lower():
                match = re.search(r"by\s+([^\n]+)", text, re.IGNORECASE)
                if match:
                    artist_name = match.group(1).strip()
                    break

    if not artist_name:
        raise RuntimeError(
            "Could not determine artist name from this Wikipedia page. "
            "Try a different album page, or use an Apple Music URL instead."
        )

    # ── Parse track rows ──────────────────────────────────────────────────────
    tracks: list[dict] = []
    for row in track_rows:
        th = row.find("th")
        tds = row.find_all("td")
        if not th or len(tds) < 2:
            continue
        try:
            track_number = int(re.sub(r"\D", "", th.get_text(strip=True)))
        except ValueError:
            continue

        title = tds[0].get_text(separator=" ", strip=True)
        title = re.sub(r"\(.*?\)", "", title).strip('"""')

        raw_length = tds[-1].get_text(strip=True)
        duration_match = re.search(r"\d+:\d{2}", raw_length)
        duration = duration_match.group() if duration_match else ""

        tracks.append({
            "disc_number": 1,
            "track_number": track_number,
            "track_title": title,
            "artist_name": artist_name,
            "album_name": album_name,
            "track_duration": duration,
        })

    if not tracks:
        raise RuntimeError(
            "A track listing table was found but no tracks could be parsed from it."
        )

    return album_name, artist_name, tracks
