# parser.py

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os
import argparse
from urllib.parse import urlparse
import sys

def clean_album_title(raw_title: str) -> str:
    return re.sub(r'\s*\(.*?\)\s*', '', raw_title).strip()

def extract_album_data_wiki(wikipedia_url: str, base_music_dir: str, dry_run: bool = False, artist_name: str = None) -> pd.DataFrame:
    response = requests.get(wikipedia_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    tables = soup.find_all('table')
    if not tables:
        raise Exception("No tables found on Wikipedia page.")

    candidate_tables = []
    for idx, table in enumerate(tables):
        headers = [th.get_text(strip=True).lower() for th in table.find_all('th')]
        print(f"\nTable {idx} headers: {headers}")
        if 'title' in headers and 'length' in headers:
            candidate_tables.append((idx, table, headers))

    if not candidate_tables:
        print("[ERROR] No obvious tracklist table found.")
        raise Exception("No obvious tracklist table found and cannot prompt for input in GUI mode.")

    else:
        table_idx, tracklist_table, headers = candidate_tables[0]
        print(f"\nUsing Table {table_idx} as the tracklist table.")

    nested_table = tracklist_table.find('table')
    if nested_table:
        print("[INFO] Nested table detected. Using nested tracklist.")
        track_rows = nested_table.find_all('tr')[1:]
    else:
        track_rows = tracklist_table.find_all('tr')[1:]

    album_title_raw = soup.find('h1').text.strip()
    album_title = clean_album_title(album_title_raw)

    if not artist_name:
        infobox = soup.find('table', class_='infobox')
        if infobox:
            for row in infobox.find_all('tr'):
                if 'by' in row.get_text().lower():
                    match = re.search(r'by\s+([^\n]+)', row.get_text(), re.IGNORECASE)
                    if match:
                        artist_name = match.group(1).strip()
                        break
        if not artist_name:
            print("[ERROR] Could not auto-detect artist.")
            raise Exception("Could not auto-detect artist and cannot prompt for input in GUI mode.")

    album_year = None
    if infobox:
        for row in infobox.find_all('tr'):
            if 'Released' in row.text:
                match = re.search(r'\b(19|20)\d{2}\b', row.text)
                if match:
                    album_year = match.group()
                    break

    data = []
    for row in track_rows:
        th = row.find('th')
        tds = row.find_all('td')
        if not th or len(tds) < 2:
            continue

        try:
            track_number = int(re.sub(r'\D', '', th.get_text(strip=True)))
        except ValueError:
            continue

        track_title = tds[0].get_text(separator=' ', strip=True)
        track_title = re.sub(r'\(.*?\)', '', track_title).strip('"“” ')
        raw_length = tds[-1].get_text(strip=True)
        duration_match = re.search(r'\d+:\d{2}', raw_length)
        track_duration = duration_match.group() if duration_match else None

        print(f"[DEBUG] {track_number}. {track_title} — {track_duration}")
        data.append({
            'track_number': track_number,
            'track_title': track_title,
            'artist_name': artist_name,
            'album_name': album_title,
            'album_year': album_year,
            'track_duration': track_duration,
            'wikipedia_album_url': wikipedia_url,
            'preferred_clip_url': None,
            'downloaded_locally': False
        })

    df = pd.DataFrame(data)

    safe_album = album_title.replace('/', '-').replace(' ', '_')
    safe_artist = artist_name.replace('/', '-').replace(' ', '_')
    album_folder_name = f"{safe_artist}_{safe_album}"
    album_folder_path = os.path.join(base_music_dir, album_folder_name)
    csv_filename = f"{safe_album}_{safe_artist}_album_tracks.csv"
    full_csv_path = os.path.join(album_folder_path, csv_filename)

    print(f"\n[DRY-RUN]" if dry_run else f"\n[✓] Saved: {csv_filename} → {album_folder_path}")

    if not dry_run:
        os.makedirs(album_folder_path, exist_ok=True)
        df.to_csv(full_csv_path, index=False)

    return df

# === CLI ===
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Universal music metadata parser")
    parser.add_argument('--type', type=str, default="wiki", help='Type of source: wiki | youtube | apple | google')
    parser.add_argument('--url', type=str, required=True, help='Source URL')
    parser.add_argument('--artist', type=str, help='Artist name (optional for some types)')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without saving')
    args = parser.parse_args()

    base_music_dir = os.path.expanduser("~/Music Downloader")

    if args.type == "wiki":
        df = extract_album_data_wiki(args.url, base_music_dir, dry_run=args.dry_run, artist_name=args.artist)
    else:
        raise NotImplementedError(f"Parser for type '{args.type}' is not implemented yet.")

    print("\nExtracted Album Data:\n")
    print(df)
