# apple_parser.py

import requests
import re
import argparse
import os
import pandas as pd

def extract_album_id(url):
    # Extract the album ID from the URL (the last number)
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

    album_name, artist_name, tracks = extract_album_info(args.url)

    if not tracks:
        print("[!] No tracks found.")
        return

    df = pd.DataFrame(tracks)

    safe_album_name = re.sub(r"\W+", "_", album_name)[:40]
    safe_artist_name = re.sub(r"\W+", "_", artist_name)[:40]

    folder_name = f"{safe_artist_name}_{safe_album_name}"
    folder_path = os.path.join(os.path.expanduser("~/Music Downloader"), folder_name)
    os.makedirs(folder_path, exist_ok=True)

    filename = f"{safe_artist_name}_{safe_album_name}_track.csv"
    filepath = os.path.join(folder_path, filename)

    if args.dry_run:
        print(f"[DRY-RUN] Would save to: {filepath}")
    else:
        df.to_csv(filepath, index=False)
        print(f"[✓] Saved: {filepath}")

    print("\nExtracted Track Data:\n")
    print(df)

if __name__ == "__main__":
    main()
