# Music Downloader

A macOS desktop app for downloading and tagging music from YouTube, Apple Music, and Wikipedia.

Built with Python + PyQt6. Dark theme, neon green aesthetic.

---

## Features

- **Album flow** — paste an Apple Music or Wikipedia album URL, preview the full track list, then download and auto-tag every track as MP3
- **Individual Links** — paste one or more YouTube URLs (single tracks or full playlists), edit titles before downloading, and get everything tagged automatically
- **Editable metadata** — review and correct track titles before any file hits disk
- **ID3 tagging** — every downloaded MP3 is tagged with title, artist, album, and track number
- **Configurable output folder** — set your download root via the Settings screen; defaults to `~/Music Downloader/`

---

## Requirements

- **Python 3.10+**
- **ffmpeg** — required by yt-dlp for MP3 conversion

Install ffmpeg via Homebrew:

```bash
brew install ffmpeg
```

---

## Setup

**1. Clone the repo**

```bash
git clone https://github.com/moseskaplan/music-downloader.git
cd music-downloader
```

**2. Install Python dependencies**

```bash
pip install -r requirements.txt
```

---

## Launching the app

```bash
python3 -m mdownloader
```

---

## How it works

### Album flow

1. Paste an **Apple Music** album URL (e.g. `https://music.apple.com/us/album/...`) or a **Wikipedia** album page URL
2. The app fetches the track list and shows a preview table with title, artist, duration, and track number
3. Click **Download** — each track is downloaded from YouTube, converted to MP3, and tagged with ID3 metadata
4. Files are saved to `<download root>/<Artist>/<Album>/`

### Individual Links flow

1. Paste one or more **YouTube URLs** — one per row
2. Toggle the **Playlist** checkbox on any row to expand a full YouTube playlist (up to 50 tracks)
3. Click **Get Track(s)** — metadata is fetched in the background
4. Review the track list; click any title to edit it before downloading
5. Click **Confirm & Download** — progress shown live in the button (`Downloading 1/N …`)
6. Singles are saved to `<download root>/Singles/<Artist or Playlist Name>/`

---

## Output folder structure

```
<download root>/
├── <Artist>/
│   └── <Album>/
│       ├── 01 - Artist - Title.mp3
│       └── 02 - Artist - Title.mp3
└── Singles/
    ├── <Artist>/
    │   └── Artist - Title.mp3
    └── <Playlist Name>/
        ├── Artist - Title.mp3
        └── ...
```

The download root defaults to `~/Music Downloader/` and can be changed in **Settings**.

---

## Project structure

```
music-downloader/
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
└── mdownloader/
    ├── __main__.py          # Entry point
    ├── version.py
    ├── config.py            # JSON config (~/Library/Application Support/Music Downloader/)
    ├── core/
    │   └── utils.py         # Shared helpers
    ├── gui_qt/
    │   ├── app.py           # QApplication setup
    │   ├── style.py         # Dark theme + neon green stylesheet
    │   ├── windows/
    │   │   ├── home.py      # Home screen
    │   │   ├── album_flow.py
    │   │   ├── links_flow.py
    │   │   └── settings.py
    │   ├── workers/
    │   │   ├── album_download_worker.py
    │   │   └── metadata_fetch_worker.py
    │   └── models/
    │       └── track_table_model.py
    ├── parsers/
    │   ├── apple.py         # iTunes API parser
    │   └── wiki.py          # Wikipedia album scraper
    └── services/
        ├── downloader.py    # yt-dlp download + ID3 tagging
        └── youtube_metadata.py  # Metadata-only fetch (no download)
```

---

## Running tests

```bash
pytest
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| PyQt6 | Desktop GUI |
| yt-dlp | YouTube audio download |
| mutagen | ID3 metadata tagging |
| requests | HTTP requests (Apple Music / Wikipedia) |
| beautifulsoup4 + lxml | Wikipedia HTML parsing |
| rapidfuzz | Fuzzy track title matching |
| ffmpeg *(system)* | MP3 conversion (not a Python package) |

---

## Version

`0.1.0` — initial release
