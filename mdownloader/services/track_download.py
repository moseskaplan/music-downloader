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
from pathlib import Path

import pandas as pd
from youtubesearchpython import VideosSearch
import yt_dlp

from mdownloader.core.utils import parse_duration_str, clean_filename


def download_album_tracks(csv_path: str, workers: int = 1, test_mode: bool = False) -> None:
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

    # Define a worker function for downloading a single track
    def process_track(task_idx: int, row: pd.Series) -> None:
        track_number = row['track_number']
        title = clean_filename(str(row['track_title']))
        artist = clean_filename(str(row['artist_name']))
        album = clean_filename(str(row['album_name']))
        desired_duration = parse_duration_str(row['track_duration'])

        print(f"[{task_idx}/{total_tracks}] Starting: {artist} - {title}")

        if not desired_duration:
            print(f"[{task_idx}/{total_tracks}] [!] Skipping {title} — invalid duration: {row['track_duration']}")
            return

        query = f"{artist} {title} audio"
        print(f"[{task_idx}/{total_tracks}] [-] Searching: {query}")

        search = VideosSearch(query, limit=5)
        results = search.result().get('result', [])
        best_match = None
        for result in results:
            video_url = result['link']
            video_duration = parse_duration_str(result.get('duration', '0:00'))
            if video_duration and abs(video_duration - desired_duration) <= 3:
                best_match = video_url
                break
        if not best_match:
            print(f"[{task_idx}/{total_tracks}] [!] No duration-matched video found for: {title}")
            return
        print(f"[{task_idx}/{total_tracks}] [✓] Found match: {best_match}")

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
            # Skip actual download in test mode
            print(f"[{task_idx}/{total_tracks}] [TEST-MODE] Would save: {full_path}")
            return
        # Remove the .mp3 suffix so yt_dlp will append a single .mp3 when converting
        stem = os.path.splitext(filename)[0]
        ydl_opts = {
            # Prefer m4a when available, then bestaudio
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            # Use the stem as the output template so ffmpeg only appends one extension
            'outtmpl': os.path.join(album_folder, stem),
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }
            ],
        }
        try:
            print(f"[{task_idx}/{total_tracks}] [↓] Downloading: {filename} ...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([best_match])
            print(f"[{task_idx}/{total_tracks}] [✓] Saved: {filename} to {album_folder}\n")
        except Exception as e:
            print(f"[{task_idx}/{total_tracks}] [!] Error downloading {title}: {e}")

    # If workers <= 1, run sequentially
    if workers <= 1:
        for idx, (_, row) in enumerate(df.iterrows(), 1):
            process_track(idx, row)
    else:
        # Use ThreadPoolExecutor for concurrent downloads
        from concurrent.futures import ThreadPoolExecutor, as_completed
        tasks = []
        # Submit tasks for all tracks
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for idx, (_, row) in enumerate(df.iterrows(), 1):
                tasks.append(executor.submit(process_track, idx, row))
            # Wait for all tasks to complete
            for f in as_completed(tasks):
                # exceptions are raised here if any
                try:
                    f.result()
                except Exception as ex:
                    # Print exception but continue
                    print(f"[!] Worker error: {ex}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download MP3 tracks for an album using a CSV tracklist.")
    parser.add_argument("csv_path", help="Path to the album tracklist CSV")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of concurrent downloads (default: 1, meaning sequential)")
    parser.add_argument("--test-mode", action="store_true", help="Preview actions without downloading files")
    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        print(f"[!] File not found: {args.csv_path}")
        return
    # Ensure workers is at least 1
    workers = args.workers if args.workers and args.workers > 0 else 1
    download_album_tracks(args.csv_path, workers=workers, test_mode=args.test_mode)


if __name__ == "__main__":
    main()