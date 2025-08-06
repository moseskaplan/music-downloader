import subprocess
import argparse
import sys
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import shutil

# Version information
from version import VERSION, get_git_revision

# === CLI args ===
parser = argparse.ArgumentParser(description="Cascade music downloader scripts.")
parser.add_argument("--url", nargs="+", help="One or more album/song URLs")
# Allow --type to be optional. If omitted, run_all will auto-detect the correct parser
parser.add_argument("--type", choices=["wiki", "youtube", "search", "apple"],
                    help="Source type (wiki, youtube, search, apple). If omitted, the type will be inferred from the URL.")
parser.add_argument("--skip-parse", action="store_true", help="Skip parser step")
parser.add_argument("--skip-download", action="store_true", help="Skip track_download.py")
parser.add_argument("--skip-tag", action="store_true", help="Skip track_metadata_cleanup.py")
parser.add_argument("--summary", action="store_true", help="Print summary after all steps.")
parser.add_argument("--test-mode", action="store_true", help="Enable test mode (always cleans up temp data at end)")
parser.add_argument("--no-cleanup", action="store_true", help="Skip cleanup of temp folder in test mode (for debugging)")
args = parser.parse_args()

# === CONFIG ===
base_dir = os.path.expanduser("~/Music Downloader")
log_dir = os.path.join(base_dir, "0 Run Logs")
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_path = os.path.join(log_dir, f"run_log_{timestamp}.txt")

# === Temp dir helper ===
def get_tmp_dir():
    """Return correct temporary directory based on mode."""
    return Path("/tmp/music_downloader_test") if args.test_mode else Path("/tmp/music_downloader_dryrun")

def write_log(message):
    if message is None:
        return
    with open(log_path, "a") as f:
        f.write(str(message) + "\n")
    print(message, flush=True)

def clear_tmp_dir():
    tmp_dir = get_tmp_dir()
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    write_log(f"[TEST-MODE] Cleared temp cache: {tmp_dir}")

def remove_tmp_dir():
    tmp_dir = get_tmp_dir()
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
        write_log(f"[TEST-MODE] Removed temp cache: {tmp_dir}")

# Always start fresh in test mode
if args.test_mode:
    clear_tmp_dir()

def run_script(script_name, *extra_args, required=True):
    """Helper to run a script and log the result."""
    cmd = ["python3", script_name] + list(extra_args)
    if args.test_mode:
        cmd.append("--test-mode")  # Pass down to all steps
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
    """Find the most recently modified CSV after a given timestamp."""
    search_dir = get_tmp_dir() if args.test_mode else Path(base_dir)
    latest_csv = None
    latest_time = after_timestamp

    if not search_dir.exists():
        return None

    for folder in search_dir.glob("*_*"):
        for csv_file in folder.glob("*.csv"):
            mod_time = csv_file.stat().st_mtime
            if mod_time > latest_time:
                latest_time = mod_time
                latest_csv = csv_file

    return str(latest_csv) if latest_csv else None

def detect_type(url: str) -> str:
    """Infer the parser type from the given URL.

    Returns one of "wiki", "youtube", "apple", or "search". The function
    examines the domain to make a best guess. If none match, it falls back
    to "search".
    """
    lower = url.lower()
    if "wikipedia.org" in lower:
        return "wiki"
    if "youtube.com" in lower or "youtu.be" in lower:
        return "youtube"
    if "music.apple.com" in lower or "itunes.apple.com" in lower:
        return "apple"
    return "search"

def run_step(step_num, description, script_name, extra_args=None, csv_path=None):
    """Run a single pipeline step and always stop on failure."""
    write_log(f"\n=== STEP {step_num}: {description} ===")
    args_list = extra_args or []
    if csv_path:
        args_list.insert(0, csv_path)

    success = run_script(script_name, *args_list)
    if not success:
        write_log(f"[🛑 STOPPED] {description} failed.")
        return False

    write_log(f"[✅] {description} succeeded.\n")
    return True

def main():
    if not args.url:
        write_log("[🛑 ERROR] You must pass at least one URL via --url")
        sys.exit(1)

    # Log version information once at the start of the run
    write_log(f"[INFO] Music Downloader version {VERSION} ({get_git_revision()})")

    parser_script_map = {
        "wiki": "wiki_parser.py",
        "youtube": "youtube_parser.py",
        "search": "search_parser.py",
        "apple": "apple_parser.py"
    }

    # If --type was not provided, infer it from the first URL
    parser_type = args.type
    if parser_type is None:
        parser_type = detect_type(args.url[0])
        write_log(f"[INFO] Auto‑detected type '{parser_type}' for URL: {args.url[0]}")

    parser_script = parser_script_map.get(parser_type)
    if not parser_script:
        write_log(f"[🛑 ERROR] Unknown type: {parser_type}")
        sys.exit(1)

    all_csv_paths = []

    for url in args.url:
        write_log(f"\n🔗 Processing URL: {url}")
        csv_path = None
        pre_parse_time = datetime.now().timestamp()

        # === STEP 1: Parse ===
        if not args.skip_parse:
            if not run_step(1, "Parsing", parser_script, ["--url", url]):
                continue
            csv_path = find_latest_csv(pre_parse_time)
            if not csv_path:
                write_log("[🛑 STOPPED] Could not locate new CSV output.")
                continue

        # === STEP 2: Download ===
        if not args.skip_download:
            if not run_step(2, "Downloading", "track_download.py", [csv_path]):
                continue

        # === STEP 3: Tag ===
        if not args.skip_tag:
            if not run_step(3, "Tagging", "track_metadata_cleanup.py", [csv_path]):
                continue

        all_csv_paths.append(csv_path)

    # === SUMMARY ===
    if args.summary:
        write_log("\n=== SUMMARY ===")
        for path in all_csv_paths:
            if path:
                folder = Path(path).parent.name
                try:
                    df = pd.read_csv(path)
                    track_count = len(df)
                except Exception:
                    track_count = "?"
                write_log(f"{folder} — {track_count} tracks")

    # === TEST-MODE CLEANUP ===
    if args.test_mode and not args.no_cleanup:
        remove_tmp_dir()

write_log(f"[⚙️ MODE] Running in {'TEST-MODE' if args.test_mode else 'real'} mode.")

if __name__ == "__main__":
    main()
