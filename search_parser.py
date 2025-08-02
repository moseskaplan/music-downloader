# search_parser.py
import argparse
import os
import pandas as pd
from yt_dlp import YoutubeDL
from urllib.parse import unquote, urlparse, parse_qs

def extract_search_query(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query).get("q", [""])[0]
    return unquote(query)

def search_youtube_tracks(query, max_results=5):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'extract_flat': 'in_playlist',
        'format': 'bestaudio/best',
        'default_search': 'ytsearch',
        'noplaylist': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        return info.get("entries", [])

def main():
    parser = argparse.ArgumentParser(description="Parse track names from YouTube search results.")
    parser.add_argument("--url", required=True, help="Google search URL")
    parser.add_argument("--dry-run", action="store_true", help="Only simulate and log actions.")
    args = parser.parse_args()

    search_query = extract_search_query(args.url)
    print(f"[DEBUG] Extracted query: {search_query}")

    tracks = search_youtube_tracks(search_query)
    if not tracks:
        print("[!] No tracks found in YouTube search.")
        return

    artist_name = search_query.split()[0]
    track_data = []
    for i, entry in enumerate(tracks, 1):
        title = entry.get("title", "")
        url = f"https://www.youtube.com/watch?v={entry.get('id')}"
        duration = entry.get("duration_string", "")

        track_data.append({
            "track_number": None,
            "track_title": title,
            "album_name": "",
            "artist_name": artist_name,
            "track_duration": duration,
            "wikipedia_album_url": args.url,
            "preferred_clip_url": url,
            "downloaded_locally": False
        })

    df = pd.DataFrame(track_data)

    folder_name = f"{artist_name}_{search_query.replace(' ', '_')[:40]}"
    folder_path = os.path.join(os.path.expanduser("~/Music Downloader"), folder_name)
    os.makedirs(folder_path, exist_ok=True)

    filename = f"{artist_name}_{search_query.replace(' ', '_')}_track.csv"
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
