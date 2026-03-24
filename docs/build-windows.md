# Building Music Downloader for Windows

Step-by-step instructions for building the Windows `.exe` on a Windows machine.

---

## Prerequisites

### 1. Install Python 3.13

Download from https://www.python.org/downloads/windows/

- Choose **Windows installer (64-bit)**
- During install: **check "Add python.exe to PATH"** — this is important
- Verify in a new terminal:
  ```
  python --version
  ```
  Should show `Python 3.13.x`

---

### 2. Install Git

Download from https://git-scm.com/download/win

- Use default options throughout
- Verify:
  ```
  git --version
  ```

---

### 3. Clone the repo

Open a terminal (Command Prompt or PowerShell) and run:

```
git clone https://github.com/moseskaplan/music-downloader.git
cd music-downloader
```

---

### 4. Install Python dependencies

```
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

---

### 5. Install ffmpeg

1. Download a Windows build from https://www.gyan.dev/ffmpeg/builds/
   - Get the **ffmpeg-release-essentials.zip** (under "release builds")
2. Extract the zip
3. Inside the extracted folder find `bin\ffmpeg.exe`
4. Create the folder `C:\ffmpeg\bin\` and copy `ffmpeg.exe` into it

Verify:
```
C:\ffmpeg\bin\ffmpeg.exe -version
```

---

## Building the .exe

From the `music-downloader` folder, run:

```
python -m PyInstaller MusicDownloader-Windows.spec
```

This will take a few minutes. When it finishes you'll see:

```
Building COLLECT ... completed successfully.
```

The output is in:
```
dist\MusicDownloader\MusicDownloader.exe
```

Double-click `MusicDownloader.exe` to test it.

---

## Troubleshooting

**If the build fails with a missing module error:**
- Note the module name and report it — we'll add it to the `hiddenimports` list in the spec file.

**If the .exe launches but crashes immediately:**
- Run it from a terminal to see the error output:
  ```
  dist\MusicDownloader\MusicDownloader.exe
  ```

**If ffmpeg is not found at runtime:**
- Confirm `C:\ffmpeg\bin\ffmpeg.exe` exists before building.
- The spec file bundles ffmpeg from that path at build time.

---

## Sharing results

Drop screenshots and any error output into:
```
Google Drive / My Drive / MAKK / AI Projects / Music Downloader / Claude Code Desktop App
```

That folder is shared with the Mac for debugging.
