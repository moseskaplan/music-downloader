"""Wikipedia album parser for the music downloader.

This module scrapes track lists from Wikipedia album pages.  It
attempts to find a table containing song titles and durations and
returns a structured DataFrame.  The output CSV is written to a
folder in the user's music directory (``~/Music Downloader``) or to a
temporary directory when running in test mode.

Usage as a script:
    python3 -m mdownloader.parsers.wiki --url <wikipedia_url> [--artist <name>] [--test-mode]
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pandas as pd
import requests
from bs4 import BeautifulSoup

from mdownloader.core.utils import get_tmp_dir


def clean_wiki_url(original_url: str) -> str:
    """Remove query parameters and fragments from a Wikipedia URL."""
    parsed = urlparse(original_url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))


def clean_album_title(raw_title: str) -> str:
    """Strip parenthetical descriptors from an album title."""
    return re.sub(r'\s*\(.*?\)\s*', '', raw_title).strip()


def extract_album_data_wiki(wikipedia_url: str, test_mode: bool = False, artist_name: str | None = None) -> pd.DataFrame:
    """Scrape a Wikipedia album page and build a DataFrame of tracks.

    Args:
        wikipedia_url: The URL of the album's Wikipedia page.
        test_mode: If True, write output to a temporary directory.
        artist_name: Optional artist name override; if omitted the
            function attempts to extract it from the page infobox.

    Returns:
        A pandas DataFrame containing track metadata.

    Raises:
        Exception: If no suitable track list table can be located or
            artist name cannot be determined.
    """
    wikipedia_url = clean_wiki_url(wikipedia_url)
    print(f"[DEBUG] Cleaned Wikipedia URL: {wikipedia_url}")
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
    table_idx, tracklist_table, headers = candidate_tables[0]
    print(f"\nUsing Table {table_idx} as the tracklist table.")

    # Handle nested tables within the tracklist
    nested_table = tracklist_table.find('table')
    if nested_table:
        print("[INFO] Nested table detected. Using nested tracklist.")
        track_rows = nested_table.find_all('tr')[1:]
    else:
        track_rows = tracklist_table.find_all('tr')[1:]

    # Extract album and artist information
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
    infobox = soup.find('table', class_='infobox')
    if infobox:
        for row in infobox.find_all('tr'):
            if 'Released' in row.text:
                match = re.search(r'\b(19|20)\d{2}\b', row.text)
                if match:
                    album_year = match.group()
                    break

    data: list[dict] = []
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
            'downloaded_locally': False,
        })

    df = pd.DataFrame(data)

    # Construct safe folder and file names
    safe_album = album_title.replace('/', '-').replace(' ', '_')
    safe_artist = artist_name.replace('/', '-').replace(' ', '_')
    album_folder_name = f"{safe_artist}_{safe_album}"

    if test_mode:
        album_folder_path = get_tmp_dir(True) / album_folder_name
        print(f"[TEST-MODE] Using temporary output path: {album_folder_path}")
    else:
        album_folder_path = Path.home() / "Music Downloader" / album_folder_name
        print(f"[✓] Output directory: {album_folder_path}")

    os.makedirs(album_folder_path, exist_ok=True)

    csv_filename = f"{safe_album}_{safe_artist}_album_tracks.csv"
    full_csv_path = album_folder_path / csv_filename
    df.to_csv(full_csv_path, index=False)

    if test_mode:
        print(f"[TEST-MODE] CSV saved to: {full_csv_path}")
    else:
        print(f"[✓] CSV saved to: {full_csv_path}")

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Wikipedia album parser")
    parser.add_argument("--url", type=str, required=True, help="Wikipedia album URL")
    parser.add_argument("--artist", type=str, help="Artist name (optional)")
    parser.add_argument("--test-mode", action="store_true", help="Enable test mode output to temp directory")
    args = parser.parse_args()

    try:
        df = extract_album_data_wiki(args.url, test_mode=args.test_mode, artist_name=args.artist)
    except Exception as exc:
        print(f"[❌ ERROR] {exc}")
        sys.exit(1)

    print("\nExtracted Album Data:\n")
    print(df)


if __name__ == "__main__":
    import sys
    main()