# run_all.py

import subprocess
import argparse
import sys
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import shutil

# === CLI args ===
parser = argparse.ArgumentParser(description="Cascade music downloader scripts.")
parser.add_argument("--url", nargs="+", help="One or more album/song URLs")
parser.add_argument("--type", choices=["wiki", "youtube", "search", "apple"], default="wiki",
                    help="Source type (wiki, youtube, search, apple)")
parser.add_argument("--skip-parse", action="store_true", help="Skip parser step")
parser.add_argument("--skip-download", action="store_true", help="Skip track_download.py")
parser.add_argument("--skip-tag", action="store_true", help="Skip track_metadata_cleanup.py")
parser.add_argument("--cascade", action="store_true", help="Stop on first failure")
parser.add_argument("--summary", action="store_true", help="Print summary after all steps.")
parser.add_argument("--dry-run", action="store_true", default=False, help="Run in dry-run mode")
args = parser.parse_args()

is_dry_run = args.dry_run

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


def clear_dryrun_tmp():
    tmp_dir = Path("/tmp/music_downloader_dryrun")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    write_log(f"[DRY-RUN] Cleared temp cache: {tmp_dir}")


if is_dry_run:
    clear_dryrun_tmp()


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
    search_dir = Path("/tmp/music_downloader_dryrun") if is_dry_run else Path(base_dir)
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


def run_step(step_num, description, script_name, extra_args=None, dry_run=False, csv_path=None, cascade=True):
    """Run a single pipeline step."""
    mode_label = "dry-run" if dry_run else "real"
    write_log(f"\n=== STEP {step_num}: {description} ({mode_label}) ===")

    args_list = extra_args or []
    if csv_path:
        args_list.insert(0, csv_path)
    if dry_run:
        args_list.append("--dry-run")

    success = run_script(script_name, *args_list)
    if cascade and not success:
        write_log(f"[🛑 STOPPED] {description} {mode_label} failed.")
        return False

    write_log(f"[✅] {description} {mode_label} succeeded.\n")
    return True


def main():
    if not args.url:
        write_log("[🛑 ERROR] You must pass at least one URL via --url")
        sys.exit(1)

    parser_script_map = {
        "wiki": "wiki_parser.py",
        "youtube": "youtube_parser.py",
        "search": "search_parser.py",
        "apple": "apple_parser.py"
    }

    parser_script = parser_script_map.get(args.type)
    if not parser_script:
        write_log(f"[🛑 ERROR] Unknown type: {args.type}")
        sys.exit(1)

    all_csv_paths = []

    for url in args.url:
        write_log(f"\n🔗 Processing URL: {url}")
        csv_path = None
        pre_parse_time = datetime.now().timestamp()

        # === STEP 1: Parse ===
        if not args.skip_parse:
            if not run_step(1, parser_script, parser_script, ["--url", url],
                            dry_run=is_dry_run, cascade=args.cascade):
                continue
            csv_path = find_latest_csv(pre_parse_time)
            if not csv_path:
                write_log("[🛑 STOPPED] Could not locate new CSV output.")
                continue

        # === STEP 2: Download ===
        if not args.skip_download:
            if not run_step(2, "track_download.py", "track_download.py", [csv_path],
                            dry_run=is_dry_run, cascade=args.cascade):
                continue

        # === STEP 3: Tag ===
        if not args.skip_tag:
            if not run_step(3, "track_metadata_cleanup.py", "track_metadata_cleanup.py", [csv_path],
                            dry_run=is_dry_run, cascade=args.cascade):
                continue

        all_csv_paths.append(csv_path)

    # === Summary ===
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


write_log(f"[⚙️ MODE] Running in {'dry-run' if is_dry_run else 'real'} mode.")

if __name__ == "__main__":
    main()
