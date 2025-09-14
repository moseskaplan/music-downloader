"""Apple Music album parser with multi-disc support.

Queries the iTunes Lookup API to fetch track information for an Apple Music
album. Produces a CSV of all tracks across all discs.

Usage:
    python3 -m mdownloader.parsers.apple --url <album_url> [--test-mode]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pandas as pd
import requests

from mdownloader.core.utils import seconds_to_mmss, get_tmp_dir


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_apple_url(original_url: str) -> str:
    """Strip query parameters and fragments from an Apple Music URL."""
    parsed = urlparse(original_url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def extract_album_id(url: str) -> str | None:
    """Extract the numeric album identifier from an Apple Music URL."""
    match = re.search(r"/album/.*?/(\d+)", url)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def extract_album_info(url: str) -> tuple[str, str, list[dict]]:
    """Query the Apple API and build a track list for an album."""
    album_id = extract_album_id(url)
    if not album_id:
        print("[!] Could not extract album ID from URL.")
        return "Unknown Album", "Unknown Artist", []

    api_url = f"https://itunes.apple.com/lookup?id={album_id}&entity=song"
    retries = 3
    data = None
    for attempt in range(retries):
        try:
            resp = requests.get(api_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            break
        except requests.exceptions.HTTPError as exc:
            status = resp.status_code if "resp" in locals() else None
            if status and (status == 429 or 500 <= status < 600):
                wait = 2 ** attempt
                print(f"[!] Apple API status {status}; retrying in {wait}s...")
                time.sleep(wait)
                continue
            print(f"[!] Apple API HTTP error: {exc}")
            return "Unknown Album", "Unknown Artist", []
        except Exception as exc:
            print(f"[!] Apple API request failed: {exc}")
            return "Unknown Album", "Unknown Artist", []

    if data is None:
        print("[!] Exceeded retries contacting Apple API.")
        return "Unknown Album", "Unknown Artist", []

    results = data.get("results", [])
    if not results:
        print(f"[WARN] Apple API returned no results for album: {url}")
        return "Unknown Album", "Unknown Artist", []

    # first element is always the album metadata
    album_info = results[0]
    album_name = album_info.get("collectionName", "Unknown Album")
    artist_name = album_info.get("artistName", "Unknown Artist")

    if len(results) < 2:
        # album metadata exists but there are no track objects
        print(f"[WARN] Apple API returned album metadata but no tracks for: {url}")
        return album_name, artist_name, []

    # --- normal track processing below ---
    track_rows: list[tuple[int, int, dict]] = []
    for item in results[1:]:
        if item.get("wrapperType") != "track":
            continue
        disc = item.get("discNumber", 1) or 1
        num = item.get("trackNumber", 0) or 0
        track_rows.append((disc, num, item))

    track_rows.sort(key=lambda x: (x[0], x[1]))

    tracks: list[dict] = []
    seq = 1
    for disc, num, raw in track_rows:
        title = raw.get("trackName")
        if not title:
            continue
        duration = (raw.get("trackTimeMillis") or 0) // 1000
        preview = raw.get("previewUrl")
        if not preview:
            print(f"[WARN] No preview URL for: Disc {disc} Track {num} – {title}")
        tracks.append(
            {
                "track_number": seq,
                "track_title": title,
                "album_name": album_name,
                "artist_name": artist_name,
                "track_duration": seconds_to_mmss(duration),
                "wikipedia_album_url": url,
                "preferred_clip_url": preview or "",
                "downloaded_locally": False,
                "disc_number": disc,
            }
        )
        seq += 1

    return album_name, artist_name, tracks



# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Parse Apple Music album pages.")
    parser.add_argument("--url", required=True, help="Apple Music album URL")
    parser.add_argument(
        "--test-mode", action="store_true", help="Write CSV to /tmp for testing"
    )
    args = parser.parse_args()

    cleaned = clean_apple_url(args.url)
    print(f"[DEBUG] Cleaned URL: {cleaned}")

    try:
        album_name, artist_name, tracks = extract_album_info(cleaned)
    except Exception:
        import traceback
        print("[❌ ERROR] Unexpected failure parsing album:")
        traceback.print_exc()
        sys.exit(1)

    # === Handle no tracks ===
    if not tracks:
        print("[WARN] Parser found 0 tracks. Album may be restricted or previews hidden.")
        empty_df = pd.DataFrame(columns=[
            "track_number", "track_title", "album_name", "artist_name",
            "track_duration", "wikipedia_album_url", "preferred_clip_url",
            "downloaded_locally", "disc_number"
        ])
        safe_album = re.sub(r"\W+", "_", album_name)[:40]
        safe_artist = re.sub(r"\W+", "_", artist_name)[:40]
        filename = f"{safe_artist}_{safe_album}_track.csv"
        out_dir = get_tmp_dir(True) if args.test_mode \
            else Path.home() / "Music Downloader" / f"{safe_artist}_{safe_album}"
        os.makedirs(out_dir, exist_ok=True)
        csv_path = out_dir / filename
        empty_df.to_csv(csv_path, index=False)
        if args.test_mode:
            print(f"[TEST-MODE] Empty CSV saved to: {csv_path}")
        else:
            print(f"[✓] Empty CSV saved to: {csv_path}")
        sys.exit(0)

    # === Normal case: we have tracks ===
    df = pd.DataFrame(tracks)
    safe_album = re.sub(r"\W+", "_", album_name)[:40]
    safe_artist = re.sub(r"\W+", "_", artist_name)[:40]
    filename = f"{safe_artist}_{safe_album}_track.csv"
    out_dir = get_tmp_dir(True) if args.test_mode \
        else Path.home() / "Music Downloader" / f"{safe_artist}_{safe_album}"

    os.makedirs(out_dir, exist_ok=True)
    csv_path = out_dir / filename
    df.to_csv(csv_path, index=False)

    if args.test_mode:
        print(f"[TEST-MODE] CSV saved to: {csv_path}")
    else:
        print(f"[✓] CSV saved to: {csv_path}")

    print("\nExtracted Track Data:\n")
    print(df)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        print("[❌ ERROR] Apple parser crashed:")
        traceback.print_exc()
        sys.exit(1)

