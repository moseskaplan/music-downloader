"""Search parser for the music downloader.

This module implements a very simple YouTube search based on a query
encoded in a URL (e.g. ``https://google.com/search?q=artist+song``).
It extracts the ``q`` parameter from the URL, performs a YouTube search
via ``yt_dlp`` and writes the first few results into a CSV.  The
generated files reside in the user's music folder or a temporary
directory when running in test mode.

NOTE: The search parser is provided as a proof of concept and should
eventually be replaced with official APIs where available.
"""

from __future__ import annotations

import argparse
import os
from urllib.parse import unquote, urlparse, parse_qs
from pathlib import Path

import pandas as pd
from yt_dlp import YoutubeDL

from mdownloader.core.utils import get_tmp_dir


def extract_search_query(url: str) -> str:
    """Return the value of the ``q`` parameter from a query URL."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query).get("q", [""])[0]
    return unquote(query)


def search_youtube_tracks(query: str, max_results: int = 5) -> list[dict]:
    """Use yt_dlp to perform a YouTube search and return entry metadata."""
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': 'in_playlist',
        'format': 'bestaudio/best',
        'default_search': 'ytsearch',
        'noplaylist': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        return info.get("entries", [])


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse track names from YouTube search results.")
    parser.add_argument("--url", required=True, help="Search URL containing a 'q' parameter")
    parser.add_argument("--test-mode", action="store_true", help="Write output to a temporary directory")
    args = parser.parse_args()

    search_query = extract_search_query(args.url)
    print(f"[DEBUG] Extracted query: {search_query}")

    tracks = search_youtube_tracks(search_query)
    if not tracks:
        print("[!] No tracks found in YouTube search.")
        return

    # Use the first word as the artist name guess
    artist_name = search_query.split()[0] if search_query else "Unknown"
    track_data = []
    for entry in tracks:
        title = entry.get("title", "")
        video_id = entry.get("id")
        url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
        duration = entry.get("duration_string", "")
        track_data.append({
            'track_number': None,
            'track_title': title,
            'album_name': "",
            'artist_name': artist_name,
            'album_year': None,
            'track_duration': duration,
            'wikipedia_album_url': args.url,
            'preferred_clip_url': url,
            'downloaded_locally': False,
        })

    df = pd.DataFrame(track_data)
    safe_artist = artist_name.replace('/', '-').replace(' ', '_')
    safe_query = search_query.replace(' ', '_')[:40]
    folder_name = f"{safe_artist}_{safe_query}"
    if args.test_mode:
        folder_path = get_tmp_dir(True) / folder_name
        print(f"[TEST-MODE] Using temporary output path: {folder_path}")
    else:
        folder_path = Path.home() / "Music Downloader" / folder_name
        print(f"[✓] Output directory: {folder_path}")

    os.makedirs(folder_path, exist_ok=True)
    filename = f"{safe_artist}_{safe_query}_track.csv"
    filepath = folder_path / filename
    df.to_csv(filepath, index=False)

    if args.test_mode:
        print(f"[TEST-MODE] CSV saved to: {filepath}")
    else:
        print(f"[✓] Saved: {filepath}")

    print("\nExtracted Track Data:\n")
    print(df)


if __name__ == "__main__":
    main()