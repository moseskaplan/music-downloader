# Music Downloader

A macOS desktop app for downloading and tagging music from YouTube, Apple Music, and Wikipedia.

Built with Python + PyQt6. Dark theme, neon green aesthetic.

---

## Features

- **Album flow** — paste an Apple Music or Wikipedia album URL, preview the full track list, paste YouTube URLs per track (or auto-fill from a YouTube playlist), then download and auto-tag every track as MP3
- **YouTube playlist auto-fill** — paste a YouTube playlist URL on the album track screen and the app fuzzy-matches playlist videos to album tracks automatically, filling in as many YouTube URLs as it can
- **Individual Links** — paste one or more YouTube URLs (single tracks or full playlists), edit titles before downloading, and get everything tagged automatically
- **Editable metadata** — review and correct track titles before any file hits disk
- **ID3 tagging** — every downloaded MP3 is tagged with title, artist, album, and track number from Apple Music / Wikipedia (not from YouTube video titles)
- **Send to Drive** — after a successful download, copy all tracks directly to a configured Google Drive folder with one click; conflicts are listed by filename before any files are overwritten
- **Configurable output folder** — set your download root and Google Drive destination folder via the Settings screen

---

## Using the packaged app

A pre-built native arm64 `.app` for macOS is available in `dist/Music Downloader.app`.

- **No Python required** — the app is self-contained
- **ffmpeg is bundled** — no need to install ffmpeg separately
- Just double-click `Music Downloader.app` to launch

---

## Running from source

### Requirements

- **miniforge arm64 Python** at `~/miniforge-arm64` (native Apple Silicon)
- **ffmpeg** — required by yt-dlp for MP3 conversion when running from source

Install miniforge:
```bash
brew install miniforge
```

Install ffmpeg:
```bash
brew install ffmpeg
```

### Setup

**1. Clone the repo**

```bash
git clone https://github.com/moseskaplan/music-downloader.git
cd music-downloader
```

**2. Install Python dependencies**

```bash
~/miniforge-arm64/bin/pip install -r requirements.txt
```

**3. Launch**

```bash
~/miniforge-arm64/bin/python3 -m mdownloader
```

---

## Building the .app

The app is packaged using PyInstaller. To rebuild:

```bash
cd music-downloader
~/miniforge-arm64/bin/pip install pyinstaller
~/miniforge-arm64/bin/pyinstaller MusicDownloader.spec
```

The output is `dist/Music Downloader.app`.

> **Note:** `MusicDownloader.spec` hardcodes the miniforge path at `~/miniforge-arm64`. If rebuilding on a different machine, update the `_QT6_PLUGINS` path in the spec to match your local PyQt6 installation.

---

## How it works

### Album flow

1. Paste an **Apple Music** album URL (e.g. `https://music.apple.com/us/album/...`) or a **Wikipedia** album page URL
2. The app fetches the track list and shows a preview table with disc, track number, title, and duration
3. **Optional:** paste a YouTube playlist URL and click **Auto-fill** — the app fuzzy-matches playlist videos to album tracks and fills in as many YouTube URLs as it can. Any unmatched rows can be filled in manually
4. Paste a YouTube URL into the **YouTube URL** column for each track you want to download; rows with no URL are skipped
5. Click **Confirm & Download** — progress shown live in the button (`Downloading 1/N …`)
6. Files are saved to `<download root>/<Artist> - <Album>/`

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
├── Artist - Album/
│   ├── 01 - Artist - Title.mp3
│   └── 02 - Artist - Title.mp3
└── Singles/
    ├── <Artist>/
    │   └── Artist - Title.mp3
    └── <Playlist Name>/
        ├── Artist - Title.mp3
        └── ...
```

The download root defaults to `~/Music Downloader/` and can be changed in **Settings**, along with the Google Drive destination folder for **Send to Drive**.

---

## Project structure

```
music-downloader/
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── MusicDownloader.spec      # PyInstaller build config
├── rthook_qt.py              # Qt plugin path runtime hook
└── mdownloader/
    ├── __main__.py          # Entry point
    ├── version.py
    ├── config.py            # JSON config (~/Library/Application Support/Music Downloader/)
    ├── core/
    │   └── utils.py         # Shared helpers
    ├── gui_qt/
    │   ├── app.py           # QApplication setup
    │   ├── style.py         # Dark theme + neon green stylesheet
    │   ├── dialogs.py       # Shared custom dialogs (download result, Send to Drive)
    │   ├── windows/
    │   │   ├── home.py      # Home screen
    │   │   ├── album_flow.py
    │   │   ├── links_flow.py
    │   │   └── settings.py
    │   ├── workers/
    │   │   ├── album_download_worker.py
    │   │   ├── metadata_fetch_worker.py
    │   │   └── playlist_fetch_worker.py  # YouTube playlist metadata fetch
    │   └── models/
    │       └── track_table_model.py
    ├── parsers/
    │   ├── apple.py         # iTunes API parser (multi-storefront fallback)
    │   └── wiki.py          # Wikipedia album scraper
    └── services/
        ├── downloader.py    # yt-dlp download + ID3 tagging
        ├── youtube_metadata.py  # Metadata-only fetch (no download)
        └── playlist_matcher.py  # rapidfuzz title matching for auto-fill
```

---

## Running tests

```bash
~/miniforge-arm64/bin/python3 -m pytest
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
| ffmpeg *(bundled in .app)* | MP3 conversion — pre-bundled for packaged app, install via Homebrew for source runs |

---

## Version

`0.1.0` — initial release
