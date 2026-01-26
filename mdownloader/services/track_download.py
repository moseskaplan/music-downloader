"""Simple MP3 downloader for preselected YouTube URLs.

This script reads a CSV produced by one of the parser modules and a
preceding selection step (``track_selector.py``) and downloads the
corresponding YouTube videos to MP3 using ``yt_dlp``.  Unlike the
original ``track_download.py``, this version contains no search or
heuristics; it simply uses the ``selected_url`` column written by
``track_selector``.  If ``selected_url`` is blank, it falls back to a
``preferred_clip_url`` if present.  Tracks with an empty URL are
skipped.  Rows marked ``selection_flag=True`` will cause the
downloaded filename to be prefixed with ``CHECK_`` to indicate
possible mismatch.

Usage::

    python3 track_download_v3.py <csv_path> [--workers N] [--test-mode]

If ``--workers`` is greater than 1, downloads will be performed
concurrently using a thread pool.  In test mode, the script prints
actions without performing network requests or file writes.

An API key is **not** required for this downloader since no YouTube
Data API calls are made.  However, you must have ``yt_dlp`` and
``ffmpeg`` installed.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional
import pandas as pd
import yt_dlp
import shutil
from mdownloader.core.utils import clean_filename


def download_from_csv(csv_path: str, workers: int = 1, test_mode: bool = False) -> None:
    """Download the YouTube URLs listed in a CSV.

    The CSV must contain either a ``selected_url`` column (preferred)
    or a ``preferred_clip_url`` column.  Each row represents a track.
    The downloader constructs an output filename based on the track
    number, artist and title.  If a row's ``selection_flag`` is true,
    the filename is prefixed with ``CHECK_``.  Tracks with no URL are
    skipped.

    Args:
        csv_path: Path to the CSV produced by the parser and selector.
        workers: Number of concurrent download threads (>=1).
        test_mode: If True, print actions instead of downloading.
    """
    try:
        df = pd.read_csv(csv_path, dtype=str)
    except Exception as exc:
        print(f"[🛑 ERROR] Failed to read CSV {csv_path}: {exc}")
        return
    if df.empty:
        print(f"[!] CSV is empty: {csv_path}")
        return
    print(f"[+] Processing file: {os.path.basename(csv_path)}")
    total_tracks = len(df)

    def process_row(task_idx: int, row: pd.Series) -> None:
        track_number = row.get('track_number')
        title = clean_filename(str(row.get('track_title', '')))
        artist = clean_filename(str(row.get('artist_name', '')))
        # Determine URL to download
        url = row.get('selected_url')
        if not url:
            url = row.get('preferred_clip_url')
        if not url or url.strip() == '':
            print(f"[{task_idx}/{total_tracks}] [!] No URL for {artist} - {title}; skipping.")
            return
        flag = False
        # If selection_flag column exists and is truthy, mark flag
        if 'selection_flag' in row and str(row['selection_flag']).lower() in ('true', '1', 'yes'):
            flag = True
        # Determine output directory (album folder)
        album_folder = os.path.dirname(csv_path)
        os.makedirs(album_folder, exist_ok=True)
        # Build filename
        if pd.isna(track_number) or str(track_number).strip() == '' or track_number is None:
            base_name = f"{artist} - {title}.mp3"
        else:
            try:
                num = int(float(track_number))
            except Exception:
                num = 1
            base_name = f"{str(num).zfill(2)} - {artist} - {title}.mp3"
        filename = base_name
        if flag:
            filename = f"CHECK_{base_name}"
        full_path = os.path.join(album_folder, filename)
        if test_mode:
            print(f"[{task_idx}/{total_tracks}] [TEST-MODE] Would download {url} to {full_path}")
            return
        stem = os.path.splitext(filename)[0]
        # Determine runtime JS support (optional)
        js_runtimes = {}
        node_path = shutil.which('node')
        deno_path = shutil.which('deno')
        if node_path:
            js_runtimes['node'] = {'path': node_path}
        if deno_path:
            js_runtimes['deno'] = {'path': deno_path}
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
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
            'concurrent_fragment_downloads': 1,
        }
        if js_runtimes:
            ydl_opts['js_runtimes'] = js_runtimes
        try:
            print(f"[{task_idx}/{total_tracks}] [↓] Downloading: {filename} from {url} …")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            print(f"[{task_idx}/{total_tracks}] [✓] Saved: {filename} to {album_folder}\n")
        except Exception as exc:
            print(f"[{task_idx}/{total_tracks}] [!] Error downloading {artist} - {title}: {exc}")

    if workers <= 1:
        for idx, row in enumerate(df.itertuples(index=False), 1):
            process_row(idx, row._asdict())
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        tasks = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for idx, row in enumerate(df.itertuples(index=False), 1):
                tasks.append(executor.submit(process_row, idx, row._asdict()))
            for f in as_completed(tasks):
                try:
                    f.result()
                except Exception as ex:
                    print(f"[!] Worker error: {ex}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download MP3 tracks from preselected YouTube URLs.")
    parser.add_argument("csv_path", help="Path to the album tracklist CSV")
    parser.add_argument("--workers", type=int, default=1, help="Number of concurrent downloads (default: 1)")
    parser.add_argument("--test-mode", action="store_true", help="Preview actions without downloading files")
    args = parser.parse_args()
    if not os.path.exists(args.csv_path):
        print(f"[🛑 ERROR] File not found: {args.csv_path}")
        return
    workers = args.workers if args.workers and args.workers > 0 else 1
    download_from_csv(args.csv_path, workers=workers, test_mode=args.test_mode)


if __name__ == "__main__":
    main()