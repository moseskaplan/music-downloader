"""Tag MP3 files with metadata from a CSV track list.

This service reads a CSV file containing track metadata and applies
ID3 tags to the corresponding MP3 files in the album folder.  It uses
the ``eyed3`` library to update titles, artists, album names and
optionally track numbers and years.  When running in test mode, no
files are modified; instead the intended operations are printed.

Usage as a script:
    python3 -m mdownloader.services.track_metadata_cleanup <csv_path> [--test-mode]
"""

from __future__ import annotations

import argparse
import os
import re
import sys

import eyed3
import pandas as pd


def tag_album_tracks(csv_path: str, test_mode: bool = False) -> None:
    """Apply metadata tags to all MP3 files in the album folder."""
    df = pd.read_csv(csv_path, dtype=str)
    if df.empty:
        print(f"[!] CSV is empty or invalid: {csv_path}")
        return
    album_dir = os.path.dirname(csv_path)
    print(f"[+] Tagging MP3s in: {album_dir}")
    if not os.path.exists(album_dir):
        print(f"[!] Album folder not found: {album_dir}")
        return
    track_map: dict[int, pd.Series] = {}
    for _, row in df.iterrows():
        track_number = row.get('track_number')
        key = 1
        if not pd.isna(track_number) and str(track_number).strip():
            try:
                key = int(float(track_number))
            except ValueError:
                key = 1
        track_map[key] = row
    for fname in os.listdir(album_dir):
        if not fname.lower().endswith(".mp3"):
            continue

        match = re.match(r"(\d+)", fname)
        row = None

        if match:
            track_num = int(match.group(1))
            row = track_map.get(track_num)
            if row is None or row.isnull().all():
                print(f"[!] No metadata for track #{track_num} in CSV")
                continue
        else:
            row = track_map.get(1)
            if row is None or row.isnull().all():
                print(f"[!] Could not extract track number from: {fname}")
                continue


                print(f"[!] Could not extract track number from: {fname}")
                continue
        filepath = os.path.join(album_dir, fname)
        if test_mode:
            print(f"[TEST-MODE] Would tag: {fname} → {row['track_title']} / {row['artist_name']} / {row['album_name']}")
            continue
        try:
            audiofile = eyed3.load(filepath)
            if audiofile is None:
                print(f"[!] Failed to load: {filepath}")
                continue
            if audiofile.tag is None:
                audiofile.initTag()
            audiofile.tag.title = row['track_title']
            audiofile.tag.artist = row['artist_name']
            audiofile.tag.album = row['album_name']
            try:
                audiofile.tag.track_num = int(float(row['track_number']))
            except Exception:
                pass
            try:
                year = int(float(row.get('album_year')))
                audiofile.tag.recording_date = eyed3.core.Date(year)
            except Exception:
                pass
            audiofile.tag.save()
            print(f"[✓] Tagged: {fname}")
        except Exception as e:
            print(f"[X] Error tagging {fname}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tag MP3s using metadata from a CSV.")
    parser.add_argument("csv_path", nargs="?", help="Path to the album track CSV file.")
    parser.add_argument("--test-mode", action="store_true", help="Preview tagging without modifying files.")
    args = parser.parse_args()
    if not args.csv_path:
        args.csv_path = input("Enter full path to the CSV file (e.g., from Music Downloader): ").strip()
    if not os.path.exists(args.csv_path):
        print(f"[!] File not found: {args.csv_path}")
        sys.exit(1)
    tag_album_tracks(args.csv_path, test_mode=args.test_mode)


if __name__ == "__main__":
    main()