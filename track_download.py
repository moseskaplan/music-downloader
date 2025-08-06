import os
import argparse
import pandas as pd
from youtubesearchpython import VideosSearch
import yt_dlp
from pathlib import Path

# Import shared helpers from utils
from utils import parse_duration_str, clean_filename




def download_album_tracks(csv_path, base_music_dir: Path, test_mode=False):
    df = pd.read_csv(csv_path, dtype=str)
    if df.empty:
        print(f"[!] CSV is empty: {csv_path}")
        return

    print(f"[+] Processing file: {os.path.basename(csv_path)}")

    total_tracks = len(df)
    for idx, (_, row) in enumerate(df.iterrows(), 1):
        track_number = row['track_number']
        title = clean_filename(str(row['track_title']))
        artist = clean_filename(str(row['artist_name']))
        album = clean_filename(str(row['album_name']))
        desired_duration = parse_duration_str(row['track_duration'])

        print(f"[{idx}/{total_tracks}] Starting: {artist} - {title}")

        if not desired_duration:
            print(f"[{idx}/{total_tracks}] [!] Skipping {title} — invalid duration: {row['track_duration']}")
            continue

        query = f"{artist} {title} audio"
        print(f"[{idx}/{total_tracks}] [-] Searching: {query}")

        search = VideosSearch(query, limit=5)
        results = search.result().get('result', [])

        best_match = None
        for result in results:
            video_url = result['link']
            video_duration = parse_duration_str(result.get('duration', '0:00'))

            if video_duration and abs(video_duration - desired_duration) <= 3:
                best_match = video_url
                break

        if not best_match:
            print(f"[{idx}/{total_tracks}] [!] No duration-matched video found for: {title}")
            continue

        print(f"[{idx}/{total_tracks}] [✓] Found match: {best_match}")

        album_folder = os.path.dirname(csv_path)
        os.makedirs(album_folder, exist_ok=True)

        if pd.isna(track_number) or track_number == "" or track_number is None:
            filename = f"{artist} - {title}.mp3"
        else:
            filename = f"{str(int(track_number)).zfill(2)} - {artist} - {title}.mp3"

        full_path = os.path.join(album_folder, filename)

        if test_mode:
            print(f"[{idx}/{total_tracks}] [TEST-MODE] Would save: {full_path}")
            continue

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(album_folder, filename.replace(".mp3", "")),
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            print(f"[{idx}/{total_tracks}] [↓] Downloading: {filename} ...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([best_match])
            print(f"[{idx}/{total_tracks}] [✓] Saved: {filename} to {album_folder}\n")
        except Exception as e:
            print(f"[{idx}/{total_tracks}] [!] Error downloading {title}: {e}")
            continue


# === Main ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download MP3 tracks for an album using a CSV tracklist.")
    parser.add_argument("csv_path", help="Path to the album tracklist CSV")
    parser.add_argument("--test-mode", action="store_true", help="Preview actions without downloading files")
    args = parser.parse_args()

    if args.test_mode:
        base_music_dir = Path("/tmp/music_downloader_test")
    else:
        base_music_dir = Path(os.path.expanduser("~/Music Downloader"))

    if not os.path.exists(args.csv_path):
        print(f"[!] File not found: {args.csv_path}")
    else:
        download_album_tracks(args.csv_path, base_music_dir, test_mode=args.test_mode)
