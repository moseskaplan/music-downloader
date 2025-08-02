# youtube_parser.py (yt_dlp version)

import yt_dlp
import argparse
import os
import pandas as pd

from urllib.parse import urlparse, parse_qs, urlunparse

def clean_youtube_url(original_url: str) -> str:
    parsed = urlparse(original_url)
    query = parse_qs(parsed.query)
    video_id = query.get("v", [None])[0]
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return original_url  # fallback


def extract_track_data(youtube_url: str, base_music_dir: str, dry_run: bool = False) -> pd.DataFrame:
    youtube_url = clean_youtube_url(youtube_url)
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'force_generic_extractor': False,
        'extract_flat': False
        
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)

    title = info.get('title', 'Unknown Title')
    artist = info.get('uploader', 'Unknown Artist')
    duration = info.get('duration')
    duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else None

    print(f"[DEBUG] Title: {title}")
    print(f"[DEBUG] Artist: {artist}")
    print(f"[DEBUG] Duration: {duration_str}")

    df = pd.DataFrame([{
        'track_number': None, # For single tracks, don't assign a number
        'track_title': title,
        'artist_name': artist,
        'album_name': title,  # Same as track if it's a single
        'album_year': None,
        'track_duration': duration_str,
        'wikipedia_album_url': youtube_url,
        'preferred_clip_url': youtube_url,
        'downloaded_locally': False
    }])

    # Clean names
    safe_artist = artist.replace('/', '-').replace(' ', '_')
    safe_title = title.replace('/', '-').replace(' ', '_')
    folder_name = f"{safe_artist}_{safe_title}"
    folder_path = os.path.join(base_music_dir, folder_name)
    os.makedirs(folder_path, exist_ok=True)

    csv_path = os.path.join(folder_path, f"{safe_title}_{safe_artist}_track.csv")

    if not dry_run:
        df.to_csv(csv_path, index=False)
        print(f"[✓] Saved: {csv_path}")
    else:
        print(f"[DRY-RUN] Would save to: {csv_path}")

    return df


# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube single-track scraper")
    parser.add_argument('--url', type=str, required=True, help='YouTube track URL')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without saving')
    args = parser.parse_args()

    base_music_dir = os.path.expanduser("~/Music Downloader")

    df = extract_track_data(args.url, base_music_dir, dry_run=args.dry_run)

    print("\nExtracted Track Data:\n")
    print(df)
