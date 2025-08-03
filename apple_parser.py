# apple_parser.py

import requests
import re
import argparse
import os
import pandas as pd
import sys
from urllib.parse import urlparse, urlunparse
from pathlib import Path

def clean_apple_url(original_url: str) -> str:
    parsed = urlparse(original_url)
    cleaned_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        "",  # strip query
        parsed.fragment
    ))
    return cleaned_url

def extract_album_id(url):
    match = re.search(r'/album/.*?/(\d+)', url)
    return match.group(1) if match else None

def extract_album_info(url):
    album_id = extract_album_id(url)
    if not album_id:
        print("[!] Could not extract album ID from URL.")
        return "Unknown Album", "Unknown Artist", []

    api_url = f"https://itunes.apple.com/lookup?id={album_id}&entity=song"
    response = requests.get(api_url)
    data = response.json()

    results = data.get("results", [])
    if not results or len(results) < 2:
        print("[!] No tracks found in API response.")
        return "Unknown Album", "Unknown Artist", []

    album_info = results[0]
    album_name = album_info.get("collectionName", "Unknown Album")
    artist_name = album_info.get("artistName", "Unknown Artist")

    tracks = []
    for i, track in enumerate(results[1:], 1):
        if track.get("wrapperType") != "track":
            continue
        tracks.append({
            "track_number": i,
            "track_title": track.get("trackName", ""),
            "album_name": album_name,
            "artist_name": artist_name,
            "track_duration": seconds_to_mmss(track.get("trackTimeMillis", 0) // 1000),
            "wikipedia_album_url": url,
            "preferred_clip_url": track.get("previewUrl", ""),
            "downloaded_locally": False
        })

    return album_name, artist_name, tracks

def seconds_to_mmss(seconds):
    if not seconds:
        return ""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"

def main():
    parser = argparse.ArgumentParser(description="Parse Apple Music album pages.")
    parser.add_argument("--url", required=True, help="Apple Music album URL")
    parser.add_argument("--test-mode", action="store_true", help="Test-mode: save to /tmp/music_downloader_test")
    args = parser.parse_args()

    raw_url = args.url
    cleaned_url = clean_apple_url(raw_url)
    print(f"[DEBUG] Cleaned URL: {cleaned_url}")

    album_name, artist_name, tracks = extract_album_info(cleaned_url)

    if not tracks:
        if args.test_mode:
            print("[TEST-MODE] No track data returned — album may be restricted on Apple Music API.")
            sys.exit(1)
        else:
            print("[!] No tracks found. Parsing failed.")
            sys.exit(1)

    df = pd.DataFrame(tracks)

    safe_album_name = re.sub(r"\W+", "_", album_name)[:40]
    safe_artist_name = re.sub(r"\W+", "_", artist_name)[:40]
    filename = f"{safe_artist_name}_{safe_album_name}_track.csv"

    # Correct temp path for test mode
    if args.test_mode:
        folder_path = Path("/tmp/music_downloader_test") / f"{safe_artist_name}_{safe_album_name}"
        print(f"[TEST-MODE] Using temporary output path: {folder_path}")
    else:
        folder_path = Path(os.path.expanduser("~/Music Downloader")) / f"{safe_artist_name}_{safe_album_name}"
        print(f"[✓] Output directory: {folder_path}")

    os.makedirs(folder_path, exist_ok=True)
    filepath = folder_path / filename

    df.to_csv(filepath, index=False)
    if args.test_mode:
        print(f"[TEST-MODE] CSV saved to: {filepath}")
    else:
        print(f"[✓] CSV saved to: {filepath}")

    print("\nExtracted Track Data:\n")
    print(df)

if __name__ == "__main__":
    main()
