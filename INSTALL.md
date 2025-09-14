# MusicDownloader – Installation Guide (macOS)

> Version 0.1.x – September 2025

## 1️⃣ Requirements
- macOS 12 or later  
- An Apple Silicon or Intel Mac

> No Python installation is required for end-users. The app is bundled as a signed `.app` inside a DMG.

---

## 2️⃣ Download & Open

1. Download `MusicDownloader.dmg` from the Releases page or from your team’s distribution link.
2. Double-click the DMG to mount it.
3. Drag **MusicDownloader.app** into the **Applications** folder (or anywhere you prefer).

---

## 3️⃣ First Launch

- The first time you open it, macOS Gatekeeper may warn:
  > “MusicDownloader” can’t be opened because it is from an unidentified developer.
- Right-click (or control-click) the app → **Open**, then choose **Open** again.  
  After the first launch, you can double-click as normal.

> Tip: If you codesign & notarize with a Developer ID, users won’t see this warning.

---

## 4️⃣ Updating

1. Download the new DMG.
2. Drag the new `MusicDownloader.app` over the old one in Applications (replace).

---

## 5️⃣ Troubleshooting

- If the app won’t launch, run from Terminal for more logs:
  /Applications/MusicDownloader.app/Contents/MacOS/MusicDownloader

Logs are written to:
~/Library/Application Support/Music Downloader/Logs

## 6️⃣ Uninstalling
Just drag MusicDownloader.app to the Trash.
(Optional) Remove logs:
rm -rf ~/Library/Application\ Support/Music\ Downloader
© 2025 – MusicDownloader Project

---

### 📌 Files to include in the PR

All changes from this packaging session plus the DMG instructions:

| File | Reason |
|------|--------|
| `mdownloader/parsers/apple.py` | multi-disc & “no tracks” handling |
| `mdownloader/core/run_all.py` | minor logging + API key check |
| `mdownloader/services/track_download.py` | fallback msg for missing API key |
| `mdownloader/tests/test_track_download_api.py` | new integration tests |
| `mdownloader/README.md` | project README |
| `INSTALL.md` | **new file** |
| `MusicDownloader.spec` | PyInstaller spec (if you plan to commit it) |

> The built DMG (`dist/MusicDownloader.dmg`) is **not** tracked in git — keep it as a release artifact.

---

### 📌 Suggested PR flow

cd ~/music-downloader/mdownloader
git checkout -b e4-packaging
# copy INSTALL.md into project root (../INSTALL.md if repo root is one level up)
git add INSTALL.md \
        mdownloader/parsers/apple.py \
        mdownloader/core/run_all.py \
        mdownloader/services/track_download.py \
        mdownloader/tests/test_track_download_api.py \
        mdownloader/README.md \
        MusicDownloader.spec
git commit -m "E4: Packaging – macOS app bundle, DMG, INSTALL.md"
git push -u origin e4-packaging
gh pr create --title "E4: Packaging & Distribution (macOS)" \
             --body "Add PyInstaller spec, DMG instructions, updated Apple parser and README. Includes INSTALL.md for end users."
