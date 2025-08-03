import os
import argparse
import pandas as pd
from youtubesearchpython import VideosSearch
import yt_dlp
from datetime import timedelta

def parse_duration_str(duration_str):
    try:
        minutes, seconds = map(int, duration_str.strip().split(":"))
        return timedelta(minutes=minutes, seconds=seconds).total_seconds()
    except:
        return None

def clean_filename(text):
    return "".join(c for c in text if c.isalnum() or c in " -_").strip()

def download_album_tracks(csv_path, base_music_dir, dry_run=False):
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

        full_path = os.path.join(album_folder, filename + ".mp3")

        if dry_run:
            print(f"[{idx}/{total_tracks}] [DRY-RUN] Would save: {full_path}")
            continue

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(album_folder, filename),
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        try:
            print(f"[{idx}/{total_tracks}] [↓] Downloading: {filename}.mp3 ...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([best_match])
            print(f"[{idx}/{total_tracks}] [✓] Saved: {filename}.mp3 to {album_folder}\n")
        except Exception as e:
            print(f"[{idx}/{total_tracks}] [!] Error downloading {title}: {e}")
            continue


# === Main ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download MP3 tracks for an album using a CSV tracklist.")
    parser.add_argument("csv_path", help="Path to the album tracklist CSV")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be downloaded without saving")
    args = parser.parse_args()

    base_music_dir = os.path.expanduser("~/Music Downloader")
    if not os.path.exists(args.csv_path):
        print(f"[!] File not found: {args.csv_path}")
    else:
        download_album_tracks(args.csv_path, base_music_dir, dry_run=args.dry_run)
