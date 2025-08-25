"""Download MP3 tracks using metadata from a CSV track list.

This service reads a CSV produced by one of the parser modules and
attempts to find matching audio on YouTube.  It uses the
``youtubesearchpython`` library to search for each song and ``yt_dlp``
to download the audio.  Files are saved into the same folder as the
CSV.  In test mode the service prints what it would do without
actually downloading files.

Usage as a script:
    python3 -m mdownloader.services.track_download <csv_path> [--test-mode]
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pandas as pd
from youtubesearchpython import VideosSearch
import yt_dlp

from mdownloader.core.utils import parse_duration_str, clean_filename


def download_album_tracks(csv_path: str, test_mode: bool = False) -> None:
    """Process a CSV file and download each track's audio.

    Args:
        csv_path: The full path to the CSV produced by a parser.
        test_mode: If True, simulate downloads without fetching audio.

    Notes:
        Tracks are downloaded into the directory containing the CSV.  If
        ``track_number`` is missing or invalid, numbering starts at 1.
    """
    df = pd.read_csv(csv_path, dtype=str)
    if df.empty:
        print(f"[!] CSV is empty: {csv_path}")
        return

    print(f"[+] Processing file: {os.path.basename(csv_path)}")

    total_tracks = len(df)
    for idx, (_, row) in enumerate(df.iterrows(), 1):
        start_time = time.time()

        track_number = row['track_number']
        title = clean_filename(str(row['track_title']))
        artist = clean_filename(str(row['artist_name']))
        album = clean_filename(str(row['album_name']))
        desired_duration = parse_duration_str(row['track_duration'])

        print(f"[{idx}/{total_tracks}] Starting: {artist} - {title}")

        if not desired_duration:
            print(f"[{idx}/{total_tracks}] [!] Skipping {title} — invalid duration: {row['track_duration']}")
            continue

        query = f"{artist} {title} audio"
        print(f"[{idx}/{total_tracks}] [-] Searching: {query}")

        search = VideosSearch(query, limit=5)
        results = search.result().get('result', [])

        if not results:
            print(f"[{idx}/{total_tracks}] [!] No YouTube results found for: {title}")
            continue

        best_match = None
        fallback_match = None

        for result in results:
            video_url = result['link']
            video_duration = parse_duration_str(result.get('duration', '0:00'))

            if not fallback_match:
                fallback_match = video_url

            if video_duration and abs(video_duration - desired_duration) <= 3:
                best_match = video_url
                break

        if not best_match:
            print(f"[{idx}/{total_tracks}] [!] No duration-matched video found for: {title}")
            if fallback_match:
                print(f"[{idx}/{total_tracks}] [~] Using fallback video: {fallback_match}")
                best_match = fallback_match
            else:
                print(f"[{idx}/{total_tracks}] [X] Skipping — no suitable match found.")
                continue

        print(f"[{idx}/{total_tracks}] [✓] Found match: {best_match}")

        album_folder = os.path.dirname(csv_path)
        os.makedirs(album_folder, exist_ok=True)

        if pd.isna(track_number) or str(track_number).strip() == "" or track_number is None:
            filename = f"{artist} - {title}.mp3"
        else:
            try:
                num = int(float(track_number))  # handle numeric strings
            except Exception:
                num = 1
            filename = f"{str(num).zfill(2)} - {artist} - {title}.mp3"

        full_path = os.path.join(album_folder, filename)

        if test_mode:
            print(f"[{idx}/{total_tracks}] [TEST-MODE] Would save: {full_path}")
            continue

        output_path = Path(album_folder) / filename

        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": str(output_path),
            "quiet": True,
            "no_warnings": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",  # This controls MP3 bitrate
                }
            ],
        }


        try:
            print(f"[{idx}/{total_tracks}] [↓] Downloading: {filename} ...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([best_match])
            print(f"[{idx}/{total_tracks}] [✓] Saved: {filename} to {album_folder}")
        except Exception as e:
            print(f"[{idx}/{total_tracks}] [!] Error downloading {title}: {e}")

        elapsed = time.time() - start_time
        print(f"[{idx}/{total_tracks}] [⏱️] Time for this track: {elapsed:.2f} seconds\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download MP3 tracks for an album using a CSV tracklist.")
    parser.add_argument("csv_path", help="Path to the album tracklist CSV")
    parser.add_argument("--test-mode", action="store_true", help="Preview actions without downloading files")
    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        print(f"[!] File not found: {args.csv_path}")
        return
    download_album_tracks(args.csv_path, test_mode=args.test_mode)


if __name__ == "__main__":
    main()
