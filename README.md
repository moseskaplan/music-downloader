# Music Downloader

A macOS desktop app for downloading albums and tracks from Apple Music, Wikipedia & YouTube.

## Requirements

- Python 3.10+
- [Anaconda](https://www.anaconda.com/) (recommended) or a standard Python environment
- `ffmpeg` (required by yt-dlp for audio conversion) — install via Homebrew:
  ```bash
  brew install ffmpeg
  ```

## Setup

**1. Install dependencies**

From the `music-downloader/` directory:
```bash
pip install -r requirements.txt
```

**2. Set the YouTube API key**

The app requires a YouTube Data API v3 key for track searching. Add it to your `~/.zshrc`:
```bash
export YOUTUBE_API_KEY="your_key_here"
```
Then reload: `source ~/.zshrc`

See [Google Cloud Console](https://console.cloud.google.com/) to create or manage API keys.

## Launching the app

Open a terminal, navigate to the `music-downloader/` directory, and run:

```bash
cd /Users/moseskaplan/Desktop/claude-practice/music-downloader
python3 -m mdownloader
```

> The `QT_QPA_PLATFORM_PLUGIN_PATH` environment variable is set permanently in `~/.zshrc`
> and is picked up automatically in any new terminal session. No prefix needed.

## Project structure

```
music-downloader/
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── mdownloader/
    ├── __main__.py              # Entry point
    ├── version.py
    ├── config.py                # JSON config (~/.../Music Downloader/config.json)
    ├── core/
    │   └── utils.py             # Shared helpers
    ├── gui_qt/
    │   ├── app.py               # QApplication setup
    │   ├── style.py             # Dark theme + neon green stylesheet
    │   ├── windows/
    │   │   └── home.py          # Home screen
    │   ├── models/              # Qt table models (Epic B)
    │   └── controllers/         # Runner/orchestration (Epic C)
    ├── parsers/                 # Apple, Wikipedia, YouTube parsers (Epic B)
    ├── services/                # Downloader, tagger, selector (Epic C/D)
    └── tests/
```

## Running tests

```bash
cd music-downloader
pytest
```
