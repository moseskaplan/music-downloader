# apple_parser.py

import requests
import re
import argparse
import os
import pandas as pd

from urllib.parse import urlparse, urlunparse

def clean_apple_url(original_url: str) -> str:
    parsed = urlparse(original_url)

    # Rebuild URL with no query parameters
    cleaned_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        "",  # ← strip query
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
    parser.add_argument("--dry-run", action="store_true", help="Only simulate and log actions.")
    args = parser.parse_args()

    raw_url = args.url
    cleaned_url = clean_apple_url(raw_url)

    print(f"[DEBUG] Cleaned URL: {cleaned_url}")

    album_name, artist_name, tracks = extract_album_info(cleaned_url)

    if not tracks:
        print("[!] No tracks found.")
        return

    df = pd.DataFrame(tracks)

    safe_album_name = re.sub(r"\W+", "_", album_name)[:40]
    safe_artist_name = re.sub(r"\W+", "_", artist_name)[:40]
    filename = f"{safe_artist_name}_{safe_album_name}_track.csv"

    if args.dry_run:
        folder_path = os.path.join("/tmp/music_downloader_dryrun", f"{safe_artist_name}_{safe_album_name}")
        print(f"[DRY-RUN] Using temporary output path: {folder_path}")
    else:
        folder_path = os.path.join(os.path.expanduser("~/Music Downloader"), f"{safe_artist_name}_{safe_album_name}")
        print(f"[✓] Output directory: {folder_path}")

    os.makedirs(folder_path, exist_ok=True)
    filepath = os.path.join(folder_path, filename)

    df.to_csv(filepath, index=False)
    print(f"[✓] CSV saved to: {filepath}")

    print("\nExtracted Track Data:\n")
    print(df)


if __name__ == "__main__":
    main()
