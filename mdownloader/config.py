"""JSON config read/write for user preferences."""

import json
from pathlib import Path

CONFIG_PATH = (
    Path.home() / "Library" / "Application Support" / "Music Downloader" / "config.json"
)

DEFAULT_CONFIG: dict = {
    "download_root_dir": str(Path.home() / "Desktop"),  # dev default; change to ~/Music Downloader for release
    "google_drive_music_dir": "",  # blank until user configures in Settings
}


def load_config() -> dict:
    """Load config from disk, merging with defaults. Resets to defaults on corrupt file."""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                data = json.load(f)
            return {**DEFAULT_CONFIG, **data}
    except Exception:
        pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Persist config dict to disk, creating parent directories as needed."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
