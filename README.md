# 🎵 Music Downloader

Music Downloader is a Python application that automates:

- Parsing album/song metadata from Apple Music, YouTube and Wikipedia.
- Selecting the best matching YouTube video using the YouTube Data API v3.
- Downloading audio tracks from YouTube via `yt_dlp`.
- Tagging MP3s with proper metadata.
- Running either as a CLI tool or a Tkinter GUI.

The goal is to make building a local, well‑tagged music library easy for both developers and non‑technical users.

---

## Features

- **Parsers** for Apple Music, YouTube (single track) and Wikipedia albums.  
- **Selector** powered by the YouTube Data API v3 to pick the most appropriate video per track.  
- **Downloader** that uses preselected URLs and `yt_dlp` for audio extraction.  
- **Metadata tagging** using `eyeD3`.  
- **Concurrent downloads** via the `--workers` flag.  
- **GUI** for non‑technical users (multi‑URL support, per‑album logs).  
- **Robust logging** (per‑album logs plus a central developer log directory).  
- **Cross‑platform** (tested on macOS and Linux; Windows support planned).

---

## Requirements

- Python 3.11 or newer  
- [FFmpeg](https://ffmpeg.org/download.html) (required by `yt_dlp`)  
- A **YouTube Data API key** (free from Google Cloud; needed for the selector step)

---

## Installation

Clone the repo and install dependencies:

```bash
git clone https://github.com/moseskaplan/music-downloader.git
cd music-downloader
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt```

Install FFmpeg if you haven’t already (for example, via Homebrew on macOS):

```bash
brew install ffmpeg```

Set your YouTube API key in the shell (replace <YOUR_KEY> with your actual key):

```bash
export YOUTUBE_API_KEY=<YOUR_KEY>```

---

## Usage (CLI)

The primary entry point is the v3 orchestrator:

```bash
python3 -m mdownloader.core.run_all_v3 --url "<album or track URL>" [options]```

---

##Key options

- --workers N  Number of concurrent download threads (default: 1).
- --skip-parse  Reuse an existing CSV instead of parsing the source.
- --skip-select  Skip the selection step (assumes selected_url already present in the CSV).
- --skip-download  Skip downloading (useful for testing the selector).
- --skip-tag  Skip MP3 tagging.
- --test-mode  Run in a temporary directory and print actions without writing files.

You can pass multiple --url arguments to process several albums or pages in one run.
