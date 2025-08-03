# tag_album_tracks.py

import os
import eyed3
import pandas as pd
import re
import argparse
import sys

def clean_title(title: str) -> str:
    """Create a safe, filesystem-compatible version of the title"""
    return "".join(c for c in title if c.isalnum() or c in " -_").strip()

def tag_album_tracks(csv_path, dry_run=False):
    df = pd.read_csv(csv_path, dtype=str)
    if df.empty:
        print(f"[!] CSV is empty or invalid: {csv_path}")
        return

    album_dir = os.path.dirname(csv_path)
    print(f"[+] Tagging MP3s in: {album_dir}")

    if not os.path.exists(album_dir):
        print(f"[!] Album folder not found: {album_dir}")
        return

    track_map = {}
    for _, row in df.iterrows():
        track_number = row.get('track_number')
        if pd.isna(track_number) or track_number == "" or track_number is None:
            key = 1  # or use a string like "single"
        else:
            key = int(track_number)
        track_map[key] = row

    for fname in os.listdir(album_dir):
        if not fname.lower().endswith(".mp3"):
            continue

        match = re.match(r"(\d+)", fname)
        if match:
            track_num = int(match.group(1))
            if track_num not in track_map:
                print(f"[!] No metadata for track #{track_num} in CSV")
                continue
            row = track_map[track_num]
        else:
            # Fallback for single tracks (no number in filename)
            if 1 in track_map:
                row = track_map[1]
            else:
                print(f"[!] Could not extract track number from: {fname}")
                continue

        filepath = os.path.join(album_dir, fname)

        if dry_run:
            print(f"[DRY-RUN] Would tag: {fname} → {row['track_title']} / {row['artist_name']} / {row['album_name']}")
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
            audiofile.tag.track_num = int(row['track_number'])

            try:
                year = int(row['album_year'])
                audiofile.tag.recording_date = eyed3.core.Date(year)
            except:
                pass

            audiofile.tag.save()
            print(f"[✓] Tagged: {fname}")

        except Exception as e:
            print(f"[X] Error tagging {fname}: {e}")

# === Main ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tag MP3s using metadata from CSV.")
    parser.add_argument("csv_path", nargs="?", help="Path to the album track CSV file.")
    parser.add_argument("--dry-run", action="store_true", help="Simulate tagging without modifying files.")

    args = parser.parse_args()

    # Manual mode fallback if no args were given
    if not args.csv_path:
        args.csv_path = input("Enter full path to the CSV file (e.g., from Music Downloader): ").strip()

    if not os.path.exists(args.csv_path):
        print(f"[!] File not found: {args.csv_path}")
        sys.exit(1)

    tag_album_tracks(args.csv_path, dry_run=args.dry_run)
