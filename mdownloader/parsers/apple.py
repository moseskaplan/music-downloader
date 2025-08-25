"""Apple Music album parser with multi‑disc support.

This module queries the iTunes Search API to fetch track information for
an Apple Music album.  It extracts the album and artist names and
constructs a list of tracks sorted by disc and track numbers.  The
resulting data is written to a CSV file in the user's music folder
(``~/Music Downloader`` by default) or in a temporary test directory
when ``--test-mode`` is specified.

Usage as a script:
    python3 -m mdownloader.parsers.apple --url <album_url> [--test-mode]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pandas as pd
import requests

from mdownloader.core.utils import seconds_to_mmss, get_tmp_dir


def clean_apple_url(original_url: str) -> str:
    """Strip query parameters and fragments from an Apple Music URL.

    Args:
        original_url: The full album URL provided by the user.

    Returns:
        A canonical URL containing only the scheme, netloc and path.
    """
    parsed = urlparse(original_url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))


def extract_album_id(url: str) -> str | None:
    """Extract the numeric album identifier from an Apple Music URL."""
    match = re.search(r'/album/.*?/(\d+)', url)
    return match.group(1) if match else None


def extract_album_info(url: str) -> tuple[str, str, list[dict]]:
    """Query the iTunes API and build a sorted track list for an album.

    This function requests metadata for the album and its tracks from the
    iTunes Search API.  It sorts tracks by disc number and track
    number and assigns sequential ``track_number`` values across discs.

    Args:
        url: A cleaned Apple Music album URL.

    Returns:
        A tuple ``(album_name, artist_name, tracks)`` where ``tracks`` is
        a list of dictionaries containing metadata for each track.

    Notes:
        If the API response does not include any tracks, the returned
        list will be empty and the caller should handle this case.
    """
    album_id = extract_album_id(url)
    if not album_id:
        print("[!] Could not extract album ID from URL.")
        return "Unknown Album", "Unknown Artist", []

    api_url = f"https://itunes.apple.com/lookup?id={album_id}&entity=song"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        print(f"[!] Failed to query Apple API: {exc}")
        return "Unknown Album", "Unknown Artist", []

    results = data.get("results", [])
    if not results or len(results) < 2:
        print("[!] No tracks found in API response.")
        return "Unknown Album", "Unknown Artist", []

    album_info = results[0]
    album_name = album_info.get("collectionName", "Unknown Album")
    artist_name = album_info.get("artistName", "Unknown Artist")

    # Collect only track entries and sort by (discNumber, trackNumber)
    track_entries = []
    for item in results[1:]:
        if item.get("wrapperType") != "track":
            continue
        disc_num = item.get("discNumber", 1)
        track_num = item.get("trackNumber", 0)
        track_entries.append((disc_num, track_num, item))

    # Sort to ensure correct ordering across multiple discs
    track_entries.sort(key=lambda tup: (tup[0], tup[1]))

    tracks: list[dict] = []
    seq = 1
    for disc_num, track_num, track in track_entries:
        # Skip entries without a track name
        title = track.get("trackName")
        if not title:
            continue
        duration_seconds = track.get("trackTimeMillis", 0) // 1000
        tracks.append({
            "track_number": seq,
            "track_title": title,
            "album_name": album_name,
            "artist_name": artist_name,
            "track_duration": seconds_to_mmss(duration_seconds),
            "wikipedia_album_url": url,
            "preferred_clip_url": track.get("previewUrl", ""),
            "downloaded_locally": False,
            "disc_number": disc_num,
        })
        seq += 1

    return album_name, artist_name, tracks


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Apple Music album pages.")
    parser.add_argument("--url", required=True, help="Apple Music album URL")
    parser.add_argument("--test-mode", action="store_true", help="Test-mode: save to temp directory")
    args = parser.parse_args()

    cleaned_url = clean_apple_url(args.url)
    print(f"[DEBUG] Cleaned URL: {cleaned_url}")

    album_name, artist_name, tracks = extract_album_info(cleaned_url)
    if not tracks:
        if args.test_mode:
            print("[TEST-MODE] No track data returned — album may be restricted on Apple Music API.")
        else:
            print("[!] No tracks found. Parsing failed.")
        sys.exit(1)

    df = pd.DataFrame(tracks)

    # Safe file and folder names
    safe_album = re.sub(r"\W+", "_", album_name)[:40]
    safe_artist = re.sub(r"\W+", "_", artist_name)[:40]
    filename = f"{safe_artist}_{safe_album}_track.csv"

    # Determine base output directory
    if args.test_mode:
        folder_path = get_tmp_dir(True) / f"{safe_artist}_{safe_album}"
        print(f"[TEST-MODE] Using temporary output path: {folder_path}")
    else:
        folder_path = Path.home() / "Music Downloader" / f"{safe_artist}_{safe_album}"
        print(f"[✓] Output directory: {folder_path}")

    os.makedirs(folder_path, exist_ok=True)
    csv_path = folder_path / filename
    df.to_csv(csv_path, index=False)

    if args.test_mode:
        print(f"[TEST-MODE] CSV saved to: {csv_path}")
    else:
        print(f"[✓] CSV saved to: {csv_path}")

    print("\nExtracted Track Data:\n")
    print(df)


if __name__ == "__main__":
    main()