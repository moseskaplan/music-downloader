# youtube_parser.py (yt_dlp version with proper --test-mode handling)

import yt_dlp
import argparse
import os
import re
import pandas as pd
from pathlib import Path

# Import shared helpers from utils
from utils import clean_youtube_url, clean_track_title

# clean_youtube_url is now provided by utils

# --- Title formatting helpers ---

# clean_track_title is now provided by utils

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

    # Extract basic metadata from yt_dlp.
    # Prefer explicit artist/track info when available; fall back to uploader/title heuristics otherwise.
    title_raw = info.get('title') or 'Unknown Title'
    # Artist priority: explicit artist → uploader → Unknown
    artist = info.get('artist') or info.get('uploader') or 'Unknown Artist'
    track_title = info.get('track')  # explicit track title if provided

    # If no explicit track, derive from the raw title using common separators.
    if not track_title or track_title.strip() == '':
        candidate = title_raw.strip()
        # Try splitting on ' - ', a common separator between artist and title
        if ' - ' in candidate:
            parts = [p.strip() for p in candidate.split(' - ') if p.strip()]
            if len(parts) >= 2:
                possible_title = parts[-2]
                possible_artist = parts[-1]
                # Update artist only if current artist is generic or matches uploader
                uploader = info.get('uploader') or ''
                if artist.lower() in ['unknown artist', uploader.lower(), possible_artist.lower()]:
                    artist = possible_artist
                track_title = possible_title
        # Try splitting on '|' as an alternative delimiter
        elif '|' in candidate:
            parts = [p.strip() for p in candidate.split('|') if p.strip()]
            if len(parts) >= 2:
                possible_title = parts[1]
                possible_artist = parts[-1]
                uploader = info.get('uploader') or ''
                if artist.lower() in ['unknown artist', uploader.lower(), possible_artist.lower()]:
                    artist = possible_artist
                track_title = possible_title
        # Fallback to the full title if still unresolved
        if not track_title or track_title.strip() == '':
            track_title = candidate

    # Clean the derived track title by removing boilerplate and normalizing "feat" patterns
    track_title = clean_track_title(track_title)

    # Compute human-readable duration
    duration = info.get('duration')
    duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else None

    print(f"[DEBUG] Title: {title_raw}")
    print(f"[DEBUG] Artist: {artist}")
    print(f"[DEBUG] Track Title: {track_title}")
    print(f"[DEBUG] Duration: {duration_str}")

    # Build DataFrame; for singles, album_name equals track_title to avoid channel names
    df = pd.DataFrame([{
        'track_number': None,
        'track_title': track_title,
        'artist_name': artist,
        'album_name': track_title,
        'album_year': None,
        'track_duration': duration_str,
        'wikipedia_album_url': youtube_url,
        'preferred_clip_url': youtube_url,
        'downloaded_locally': False
    }])

    # Clean names
    safe_artist = artist.replace('/', '-').replace(' ', '_')
    # Use the cleaned track title for folder/file naming rather than the raw title
    safe_title = track_title.replace('/', '-').replace(' ', '_')
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
