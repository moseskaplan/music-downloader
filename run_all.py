# run_all.py

import subprocess
import argparse
import sys
import os
from datetime import datetime
from pathlib import Path
import pandas as pd

# === CLI args ===
parser = argparse.ArgumentParser(description="Cascade music downloader scripts.")
parser.add_argument("--url", nargs="+", help="One or more album/song URLs")
parser.add_argument("--type", choices=["wiki", "youtube", "search", "apple"], default="wiki", help="Source type (wiki, youtube, search)")
parser.add_argument("--skip-parse", action="store_true", help="Skip wiki_parser.py or equivalent")
parser.add_argument("--skip-download", action="store_true", help="Skip download_album_tracks.py")
parser.add_argument("--skip-tag", action="store_true", help="Skip tag_album_tracks.py")
parser.add_argument("--cascade", action="store_true", help="Run sequentially and stop on failure.")
parser.add_argument("--summary", action="store_true", help="Print summary after all steps.")
parser.add_argument("--dry-run", action="store_true", default=False, help="Run dry-run steps before real steps")
args = parser.parse_args()

# === CONFIG ===
base_dir = os.path.expanduser("~/Music Downloader")
log_dir = os.path.join(base_dir, "0 Run Logs")
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_path = os.path.join(log_dir, f"run_log_{timestamp}.txt")


def write_log(message):
    if message is None:
        return
    with open(log_path, "a") as f:
        f.write(str(message) + "\n")
    print(message, flush=True)


def run_script(script_name, *args, required=True):
    """Helper to run a script and log the result."""
    cmd = ["python3", script_name] + list(args)
    write_log(f"[{datetime.now()}] ⏳ Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=required)
        write_log(result.stdout)
        if result.stderr:
            write_log(f"[stderr] {result.stderr}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        write_log(f"[❌ ERROR] {script_name} failed with exit code {e.returncode}")
        write_log(e.stderr or "No stderr output")
        if required:
            sys.exit(e.returncode)
        return False


def find_latest_csv(after_timestamp):
    music_path = Path(base_dir)
    latest_csv = None
    latest_time = after_timestamp

    for folder in music_path.glob("*_*"):
        for csv_file in folder.glob("*.csv"):
            mod_time = csv_file.stat().st_mtime
            if mod_time > latest_time:
                latest_time = mod_time
                latest_csv = csv_file

    return str(latest_csv) if latest_csv else None


def main():
    if not args.url:
        write_log("[🛑 ERROR] You must pass at least one URL via --url")
        sys.exit(1)

    parser_script_map = {
        "wiki": "wiki_parser.py",
        "youtube": "youtube_parser.py",
        "search": "search_parser.py",
        "apple": "apple_parser.py"
        # Future: add "google", "apple", etc.
    }

    parser_script = parser_script_map.get(args.type)
    if not parser_script:
        write_log(f"[🛑 ERROR] Unknown type: {args.type}")
        sys.exit(1)

    all_csv_paths = []

    for url in args.url:
        write_log(f"\n🔗 Processing URL: {url}")
        success = True
        csv_path = None

        if not args.skip_parse:
            pre_parse_time = datetime.now().timestamp()

            # Step 1: Dry run parse
            if args.dry_run:
                write_log(f"\n=== STEP 1: {parser_script} (dry-run) ===")
                success = run_script(parser_script, "--dry-run", "--url", url)
                if args.cascade and not success:
                    write_log("[🛑 STOPPED] Dry-run parsing failed.")
                    continue
                write_log("[✅] Dry-run succeeded.\n")

            # Step 1: Real parse
            write_log(f"\n=== STEP 1: {parser_script} (real) ===")
            success = run_script(parser_script, "--url", url)
            if args.cascade and not success:
                write_log("[🛑 STOPPED] Real parsing failed.")
                continue
            write_log("[✅] Real run succeeded.\n")

            # Locate the new CSV
            csv_path = find_latest_csv(pre_parse_time)
            if not csv_path:
                write_log("[🛑 STOPPED] Could not locate new CSV output.")
                continue

        # Step 2: Download
        if not args.skip_download:
            if args.dry_run:
                write_log("\n=== STEP 2: download_album_tracks.py (dry-run) ===")
                if not csv_path:
                    csv_path = input("Enter path to album CSV: ").strip()
                success = run_script("download_album_tracks.py", csv_path, "--dry-run")
                if args.cascade and not success:
                    write_log("[🛑 STOPPED] download_album_tracks.py dry-run failed.")
                    continue
                write_log("[✅] download_album_tracks.py dry-run succeeded.\n")

            write_log("\n=== STEP 2: download_album_tracks.py (real) ===")
            success = run_script("download_album_tracks.py", csv_path)
            if args.cascade and not success:
                write_log("[🛑 STOPPED] download_album_tracks.py real run failed.")
                continue
            write_log("[✅] download_album_tracks.py real run succeeded.\n")

        # Step 3: Tag
        if not args.skip_tag:
            write_log("\n=== STEP 3: tag_album_tracks.py ===")
            success = run_script("tag_album_tracks.py", csv_path)
            if args.cascade and not success:
                write_log("[🛑 STOPPED] tag_album_tracks.py failed.")
                continue
            write_log("[✅] tag_album_tracks.py succeeded.\n")

        all_csv_paths.append(csv_path)

    # Summary
    if args.summary:
        write_log("\n=== SUMMARY ===")
        for path in all_csv_paths:
            if not path:
                continue
            folder = Path(path).parent.name
            try:
                df = pd.read_csv(path)
                track_count = len(df)
            except Exception:
                track_count = "?"
            write_log(f"{folder} — {track_count} tracks")


if __name__ == "__main__":
    main()
