# youtube_parser.py (yt_dlp version with proper --test-mode handling)

import yt_dlp
import argparse
import os
import pandas as pd
from urllib.parse import urlparse, parse_qs
from pathlib import Path

def clean_youtube_url(original_url: str) -> str:
    """Extract a clean watch?v=VIDEO_ID format from the given YouTube URL."""
    parsed = urlparse(original_url)
    query = parse_qs(parsed.query)
    video_id = query.get("v", [None])[0]
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return original_url  # fallback

def extract_track_data(youtube_url: str, base_music_dir: str, test_mode: bool = False) -> pd.DataFrame:
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
        'track_number': None,  # Single track → no number
        'track_title': title,
        'artist_name': artist,
        'album_name': title,  # For singles, album = track
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

    # Correct temp path for test mode
    if test_mode:
        folder_path = Path("/tmp/music_downloader_test") / folder_name
        print(f"[TEST-MODE] Using temporary output path: {folder_path}")
    else:
        folder_path = Path(base_music_dir) / folder_name
        print(f"[✓] Output directory: {folder_path}")

    os.makedirs(folder_path, exist_ok=True)

    csv_path = folder_path / f"{safe_title}_{safe_artist}_track.csv"
    df.to_csv(csv_path, index=False)

    if test_mode:
        print(f"[TEST-MODE] CSV saved to: {csv_path}")
    else:
        print(f"[✓] CSV saved to: {csv_path}")

    return df

# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube single-track scraper")
    parser.add_argument('--url', type=str, required=True, help='YouTube track URL')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode (save to /tmp/music_downloader_test)')
    args = parser.parse_args()

    base_music_dir = os.path.expanduser("~/Music Downloader")
    df = extract_track_data(args.url, base_music_dir, test_mode=args.test_mode)

    print("\nExtracted Track Data:\n")
    print(df)
