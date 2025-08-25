"""YouTube single‑track parser for the music downloader.

This module uses ``yt_dlp`` to extract metadata from a single YouTube
video.  It derives a clean track title and artist name from the
available metadata or heuristics, writes the information to a CSV
file and reports the detected values.  The output location is either
the user's music directory or a temporary folder in test mode.

Usage as a script:
    python3 -m mdownloader.parsers.youtube --url <video_url> [--test-mode]
"""

from __future__ import annotations

import argparse
import os
import pandas as pd
from pathlib import Path

import yt_dlp

from mdownloader.core.utils import clean_youtube_url, clean_track_title, get_tmp_dir


def extract_track_data(youtube_url: str, test_mode: bool = False) -> pd.DataFrame:
    """Fetch metadata for a YouTube video and return a DataFrame with one row.

    Args:
        youtube_url: URL of the YouTube video.
        test_mode: If True, write output to a temp directory instead of the music folder.

    Returns:
        A pandas DataFrame with columns matching the downloader pipeline.
    """
    youtube_url = clean_youtube_url(youtube_url)
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'force_generic_extractor': False,
        'extract_flat': False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)

    title_raw = info.get('title') or 'Unknown Title'
    artist = info.get('artist') or info.get('uploader') or 'Unknown Artist'
    track_title = info.get('track')

    # Fallback heuristics when explicit metadata is missing
    if not track_title or track_title.strip() == '':
        candidate = title_raw.strip()
        if ' - ' in candidate:
            parts = [p.strip() for p in candidate.split(' - ') if p.strip()]
            if len(parts) == 2:
                candidate_artist, candidate_title = parts
                uploader = (info.get('uploader') or '').lower()
                if artist.lower() in ['unknown artist', uploader, candidate_artist.lower()]:
                    artist = candidate_artist
                track_title = candidate_title
            elif len(parts) >= 2:
                possible_title = parts[-2]
                possible_artist = parts[-1]
                uploader = (info.get('uploader') or '').lower()
                if artist.lower() in ['unknown artist', uploader, possible_artist.lower()]:
                    artist = possible_artist
                track_title = possible_title
        elif '|' in candidate:
            parts = [p.strip() for p in candidate.split('|') if p.strip()]
            if len(parts) >= 2:
                candidate_title = parts[1]
                candidate_artist = parts[-1]
                uploader = (info.get('uploader') or '').lower()
                if artist.lower() in ['unknown artist', uploader, candidate_artist.lower()]:
                    artist = candidate_artist
                track_title = candidate_title
        if not track_title or track_title.strip() == '':
            track_title = candidate

    track_title = clean_track_title(track_title)
    duration = info.get('duration')
    duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else None

    print(f"[DEBUG] Title: {title_raw}")
    print(f"[DEBUG] Artist: {artist}")
    print(f"[DEBUG] Track Title: {track_title}")
    print(f"[DEBUG] Duration: {duration_str}")

    df = pd.DataFrame([{ 
        'track_number': None,
        'track_title': track_title,
        'artist_name': artist,
        'album_name': track_title,
        'album_year': None,
        'track_duration': duration_str,
        'wikipedia_album_url': youtube_url,
        'preferred_clip_url': youtube_url,
        'downloaded_locally': False,
    }])

    safe_artist = artist.replace('/', '-').replace(' ', '_')
    safe_title = track_title.replace('/', '-').replace(' ', '_')
    folder_name = f"{safe_artist}_{safe_title}"

    if test_mode:
        folder_path = get_tmp_dir(True) / folder_name
        print(f"[TEST-MODE] Using temporary output path: {folder_path}")
    else:
        folder_path = Path.home() / "Music Downloader" / folder_name
        print(f"[✓] Output directory: {folder_path}")

    os.makedirs(folder_path, exist_ok=True)
    csv_path = folder_path / f"{safe_title}_{safe_artist}_track.csv"
    df.to_csv(csv_path, index=False)

    if test_mode:
        print(f"[TEST-MODE] CSV saved to: {csv_path}")
    else:
        print(f"[✓] CSV saved to: {csv_path}")

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube single-track scraper")
    parser.add_argument("--url", type=str, required=True, help="YouTube track URL")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode (write to temp)")
    args = parser.parse_args()

    df = extract_track_data(args.url, test_mode=args.test_mode)
    print("\nExtracted Track Data:\n")
    print(df)


if __name__ == "__main__":
    main()