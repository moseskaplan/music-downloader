# 🎵 Music Downloader

Music Downloader is a Python application that automates:
- Parsing album/song metadata from Apple Music, YouTube, and Wikipedia
- Downloading audio tracks from YouTube
- Tagging MP3s with proper metadata
- Running either as a CLI tool or a Tkinter GUI

The goal is to make building a local, well-tagged music library easy for both developers and non-technical users.

---

## Features

- **Parsers** for Apple Music, YouTube (single track), and Wikipedia albums  
- **Downloader** powered by YouTube Data API v3 + `yt_dlp` for audio extraction  
- **Metadata tagging** using `eyeD3`  
- **Concurrent downloads** via `--workers` flag  
- **GUI** for non-technical users (multi-URL support, logs per album)  
- **Robust logging** (per-album logs + central developer log directory)  
- **Cross-platform** (tested on macOS; Windows support planned)

---

## Requirements

- Python 3.10+  
- [FFmpeg](https://ffmpeg.org/download.html) (needed by `yt_dlp`)  
- A **YouTube Data API key** (free from Google Cloud; see below)

---

## Installation

1. Clone the repo:
   ```bash
   git clone https://github.com/moseskaplan/music-downloader.git
   cd music-downloader

pip install -r requirements.txt

brew install ffmpeg
