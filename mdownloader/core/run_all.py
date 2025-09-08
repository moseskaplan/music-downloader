"""Orchestrate the music downloader pipeline.

This script coordinates the parsing, downloading and tagging steps for one or
more provided media URLs. It handles automatic parser selection based on the
URL domain, supports test mode output to a temporary directory, logs each
operation, and writes a run log into each album folder for easy
troubleshooting.

Usage:
    python3 -m mdownloader.core.run_all --url <url1> [<url2> ...]

The --type flag may be used to force a specific parser (wiki, youtube,
search, apple). When omitted, the parser is inferred from each URL.
"""

import subprocess
import argparse
import sys
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import shutil

from mdownloader.version import VERSION, get_git_revision


# === CLI args ===
parser = argparse.ArgumentParser(description="Cascade music downloader scripts.")
parser.add_argument("--url", nargs="+", help="One or more album/song URLs")
# Allow --type to be optional. If omitted, run_all will auto-detect the correct parser
parser.add_argument("--type", choices=["wiki", "youtube", "search", "apple"],
                    help="Source type (wiki, youtube, search, apple). If omitted, the type will be inferred from the URL.")
parser.add_argument("--skip-parse", action="store_true", help="Skip parser step")
parser.add_argument("--skip-download", action="store_true", help="Skip track download step")
parser.add_argument("--skip-tag", action="store_true", help="Skip metadata tagging step")
parser.add_argument("--summary", action="store_true", help="Print summary after all steps.")
parser.add_argument("--test-mode", action="store_true", help="Enable test mode (writes to tmp directory)")
parser.add_argument("--no-cleanup", action="store_true", help="Skip cleanup of temp folder in test mode (for debugging)")
parser.add_argument("--workers", type=int, help="Number of concurrent downloads to use in the download step")
args = parser.parse_args()

# === CONFIG ===
# Base directory where downloaded music is saved
base_dir = Path.home() / "Music Downloader"
# Central log directory for developers: use Library/Application Support on macOS
# and fall back to the music folder on other platforms.
app_support_base = Path.home() / "Library/Application Support/Music Downloader"
log_dir = app_support_base / "Logs"
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_path = str(log_dir / f"run_log_{timestamp}.txt")

# === Temp dir helper ===
def get_tmp_dir() -> Path:
    """Return correct temporary directory based on mode."""
    return Path("/tmp/music_downloader_test") if args.test_mode else Path("/tmp/music_downloader_dryrun")

# === Logging ===
current_run_lines: list[str] = []

def write_log(message):
    """Write a message to the central log and accumulate it for the current run."""
    if message is None:
        return
    with open(log_path, "a") as f:
        f.write(str(message) + "\n")
    print(message, flush=True)
    # accumulate per-run messages
    current_run_lines.append(str(message))

# === API key check ===
if not args.skip_download:
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        write_log("[🛑 ERROR] YOUTUBE_API_KEY environment variable not set. "
                  "Please export it in your shell config or pass --api-key to track_download.")
        sys.exit(1)


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

def run_script(module_name: str, *extra_args, required: bool = True) -> bool:
    """Helper to run a module via `python3 -m` and log the result."""
    cmd = ["python3", "-m", module_name] + list(extra_args)
    if args.test_mode:
        # Pass test-mode flag down to all steps
        cmd.append("--test-mode")
    write_log(f"[{datetime.now()}] ⏳ Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=required)
        # Write stdout and stderr to log
        if result.stdout:
            write_log(result.stdout)
        if result.stderr:
            write_log(f"[stderr] {result.stderr}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        write_log(f"[❌ ERROR] {module_name} failed with exit code {e.returncode}")
        write_log(e.stderr or "No stderr output")
        if required:
            sys.exit(e.returncode)
        return False

def find_latest_csv(after_timestamp: float) -> str | None:
    """Find the most recently modified CSV after a given timestamp."""
    search_dir = get_tmp_dir() if args.test_mode else base_dir
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
    """Infer the parser type from the given URL."""
    lower = url.lower()
    if "wikipedia.org" in lower:
        return "wiki"
    if "youtube.com" in lower or "youtu.be" in lower:
        return "youtube"
    if "music.apple.com" in lower or "itunes.apple.com" in lower:
        return "apple"
    return "search"

def run_step(step_num: int, description: str, module_name: str, extra_args: list[str] | None = None, csv_path: str | None = None) -> bool:
    """Run a single pipeline step and stop on failure."""
    write_log(f"\n=== STEP {step_num}: {description} ===")
    args_list = extra_args.copy() if extra_args else []
    if csv_path:
        args_list.insert(0, csv_path)
    success = run_script(module_name, *args_list)
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

    # Map parser types to their module names (to be run via -m)
    parser_module_map = {
        "wiki": "mdownloader.parsers.wiki",
        "youtube": "mdownloader.parsers.youtube",
        "search": "mdownloader.parsers.search",
        "apple": "mdownloader.parsers.apple",
    }

    all_csv_paths: list[str | None] = []

    for url in args.url:
        # Reset per-run log accumulator
        global current_run_lines
        current_run_lines = []

        # Determine parser type for this URL
        parser_type = args.type or detect_type(url)
        if not args.type:
            write_log(f"[INFO] Auto‑detected type '{parser_type}' for URL: {url}")

        module_name = parser_module_map.get(parser_type)
        if not module_name:
            write_log(f"[🛑 ERROR] Unknown type: {parser_type}")
            continue

        write_log(f"\n🔗 Processing URL: {url}")
        csv_path = None
        pre_parse_time = datetime.now().timestamp()

        # === STEP 1: Parse ===
        if not args.skip_parse:
            if not run_step(1, "Parsing", module_name, ["--url", url]):
                continue
            csv_path = find_latest_csv(pre_parse_time)
            if not csv_path:
                write_log("[🛑 STOPPED] Could not locate new CSV output.")
                continue

        # === STEP 2: Download ===
        if not args.skip_download:
            # Build extra args for track download. Include workers if specified
            dl_args = [csv_path]
            if args.workers:
                dl_args += ["--workers", str(args.workers)]
            if not run_step(2, "Downloading", "mdownloader.services.track_download", dl_args):
                continue

        # === STEP 3: Tag ===
        if not args.skip_tag:
            if not run_step(3, "Tagging", "mdownloader.services.track_metadata_cleanup", [csv_path]):
                continue

        # Save run log to album folder
        if csv_path:
            try:
                album_folder = Path(csv_path).parent
                run_log_file = album_folder / "run_log.txt"
                with open(run_log_file, "w") as log_f:
                    log_f.write("\n".join(current_run_lines))
                write_log(f"[✓] Saved run log to: {run_log_file}")
            except Exception as ex:
                write_log(f"[!] Failed to save run log for {url}: {ex}")
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
