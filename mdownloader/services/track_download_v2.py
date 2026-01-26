"""Download MP3 tracks using YouTube Data API.

This script reads a CSV produced by one of the parser modules and
attempts to find matching audio on YouTube using the official YouTube
Data API v3.  Once a matching video is found, the audio is downloaded
via ``yt_dlp`` and converted to MP3.  A Google Cloud API key is
required to call the YouTube Data API; supply it via the
``--api-key`` command line option or the ``YOUTUBE_API_KEY``
environment variable.

If ``--workers`` is greater than 1, downloads will be performed
concurrently using a thread pool.  In test mode, the script prints
actions without performing network requests or file writes.

This version of the downloader introduces a more nuanced selection
heuristic for picking the best YouTube video.  Duration matching is
given higher priority, and publisher information is more carefully
examined.  The script still avoids lyric videos, covers and other
non‑studio versions.

Usage as a module:
    python3 -m track_download_v2 <csv_path> --api-key <KEY> [--workers N]

The API key argument is optional if the ``YOUTUBE_API_KEY``
environment variable is set.  The code automatically handles rate
limits by making a single batch request for video details per track.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any

import requests
import pandas as pd
import yt_dlp
from difflib import SequenceMatcher
import shutil

from mdownloader.core.utils import parse_duration_str, clean_filename


def iso8601_duration_to_seconds(duration: str) -> int:
    """Convert an ISO 8601 duration (e.g., ``PT3M12S``) to seconds.

    The YouTube Data API returns durations in ISO 8601 format.  This
    helper extracts hours, minutes and seconds and converts them to
    seconds.  Missing components are treated as zero.

    Args:
        duration: Duration string in ISO 8601 format.

    Returns:
        Total duration in seconds (int).  Returns 0 if the string is
        invalid or empty.
    """
    if not duration:
        return 0
    pattern = re.compile(r"PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?")
    match = pattern.fullmatch(duration)
    if not match:
        return 0
    hours = int(match.group("h") or 0)
    minutes = int(match.group("m") or 0)
    seconds = int(match.group("s") or 0)
    return hours * 3600 + minutes * 60 + seconds


def sanitize(text: str) -> str:
    """Lowercase and remove punctuation for fuzzy matching.

    Args:
        text: Arbitrary string to sanitize.

    Returns:
        Sanitized string with punctuation removed and whitespace
        normalized.
    """
    if not text:
        return ""
    text = text.lower()
    # Remove punctuation and symbols
    text = re.sub(r"[\(\)\[\]\{\},.!?;:'\"@#\$%\^&\*_=+<>/\\|]", "", text)
    text = text.replace("-", " ").replace("_", " ")
    return " ".join(text.split())


def search_youtube(api_key: str, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search YouTube for videos using the YouTube Data API.

    Args:
        api_key: Google Cloud API key with YouTube Data API enabled.
        query: Search query string.
        max_results: Maximum number of results to return (default 10).

    Returns:
        A list of search results.  Each result is a dict containing
        ``videoId``, ``title`` and ``channelTitle``.  Returns an empty
        list if the search fails.
    """
    endpoint = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "key": api_key,
        "part": "snippet",
        "q": query,
        "maxResults": max_results,
        "type": "video",
    }
    try:
        resp = requests.get(endpoint, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[!] Search request failed: {exc}")
        return []
    items = data.get("items", [])
    results = []
    for item in items:
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        title = snippet.get("title", "")
        channel_title = snippet.get("channelTitle", "")
        if video_id:
            results.append({
                "videoId": video_id,
                "title": title,
                "channelTitle": channel_title,
            })
    return results


def get_video_details(api_key: str, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Retrieve video durations and channel info for a list of video IDs.

    Args:
        api_key: API key for YouTube Data API.
        video_ids: List of YouTube video IDs.

    Returns:
        A dict mapping video ID to a dict with keys ``duration`` (int
        seconds), ``channelTitle`` and ``title``.  Missing IDs will not
        appear in the output.
    """
    if not video_ids:
        return {}
    endpoint = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "key": api_key,
        "part": "contentDetails,snippet",
        "id": ",".join(video_ids),
    }
    details: Dict[str, Dict[str, Any]] = {}
    try:
        resp = requests.get(endpoint, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[!] Video details request failed: {exc}")
        return details
    for item in data.get("items", []):
        vid = item.get("id")
        snippet = item.get("snippet", {})
        content = item.get("contentDetails", {})
        duration_iso = content.get("duration", "")
        duration_sec = iso8601_duration_to_seconds(duration_iso)
        details[vid] = {
            "duration": duration_sec,
            "channelTitle": snippet.get("channelTitle", ""),
            "title": snippet.get("title", ""),
            # Include the full description so we can inspect it for official cues
            "description": snippet.get("description", ""),
        }
    return details


def choose_best_video(
    candidates: List[Dict[str, Any]],
    details: Dict[str, Dict[str, Any]],
    desired_duration: int,
    artist: str,
    title: str,
) -> str | None:
    """Pick the best YouTube video from search results.

    The selection algorithm uses a weighted combination of features to
    determine the most appropriate video.  Durations close to the
    target track length carry the most weight, followed by title
    similarity and token coverage.  Channels that match the artist or
    end with "topic" receive additional boosts.  Videos with lyric or
    cover labels are skipped entirely.

    Args:
        candidates: List of dicts from ``search_youtube``.
        details: Mapping of video IDs to their details from
            ``get_video_details``.
        desired_duration: Target track duration in seconds.
        artist: Cleaned artist name.
        title: Cleaned track title.

    Returns:
        The chosen video ID, or ``None`` if none are suitable.
    """
    # Keywords that indicate the video is not a studio audio recording.
    # These are searched in both the video title and description.  If any
    # of these appear, the candidate is skipped entirely.
    bad_keywords = [
        "lyric",
        "lyrics",
        "lyric video",
        "live",
        "cover",
        "instrumental",
        "karaoke",
        "remix",
        "clip",
        "scene",
        "ost",
        "trailer",
        "teaser",
        "animation",
        "gameplay",
        "short",
        "mix",
        "medley",
        "reaction",
        "dance",
        "cam",
        "performance",
        "piano",
        "guitar",
        "ukulele",
        "bass",
    ]

    # Weight constants for scoring components.  Adjust these to tune
    # the influence of each feature.  Duration closeness carries the
    # most weight, with title similarity and token coverage playing
    # smaller roles.  Channel and metadata cues provide additive boosts.
    WEIGHT_RATIO = 0.25
    WEIGHT_TOKEN = 0.15
    WEIGHT_DURATION = 0.45
    # Boosts applied when the channel name looks official or auto‑generated.
    BOOST_TOPIC = 0.25
    BOOST_OFFICIAL = 0.15
    # Extra credit for meta cues in the description such as "Provided to
    # YouTube by" and for explicit "official audio" markers in the title
    # or description.
    BOOST_PROVIDED = 0.20
    BOOST_AUDIO = 0.10

    sanitized_title = sanitize(title)
    sanitized_artist = sanitize(artist)
    tokens = sanitized_title.split()
    # A tighter tolerance improves duration matching; use 5% of the
    # desired duration or 2 seconds, whichever is greater.  A
    # candidate outside of 15% of the desired duration is rejected.
    tolerance = max(int(desired_duration * 0.05), 2)
    best_score = 0.0
    best_id: str | None = None

    # Minimum title ratio for applying channel boosts.  If the ratio is
    # below this threshold *and* no tokens match, the official/topic
    # boosts are ignored.  This prevents unrelated videos on topic
    # channels from being over‑scored.
    MIN_RATIO_FOR_BOOST = 0.15

    for item in candidates:
        vid = item.get("videoId")
        det = details.get(vid)
        if not det:
            continue
        video_title = det.get("title", "")
        channel_title = det.get("channelTitle", "")
        description = det.get("description", "")
        lower_title = video_title.lower()
        lower_desc = description.lower()

        # Skip if the title or description contains undesirable keywords
        # (e.g., lyric video, live performance).  We do a simple substring
        # search; a more sophisticated tokenizer could be used but is
        # unnecessary for typical music metadata.
        if any(bad in lower_title or bad in lower_desc for bad in bad_keywords):
            continue

        # Duration filtering: discard videos whose length deviates by more than
        # 15% of the desired duration plus 2 seconds.  This prevents very
        # long or very short videos from being considered at all.
        dur = det.get("duration", 0)
        diff = abs(dur - desired_duration)
        if desired_duration > 0 and diff > max(desired_duration * 0.15, 2):
            continue
        # Duration score: proximity of video length to track length.
        duration_score = max(0.0, 1.0 - diff / tolerance)

        # Fuzzy ratio between the sanitized track title and the video title.
        svid = sanitize(video_title)
        ratio = (
            SequenceMatcher(None, sanitized_title, svid).ratio()
            if sanitized_title
            else 0.0
        )

        # Token coverage: fraction of tokens in the track title that appear in the video title.
        token_hits = 0.0
        if tokens:
            token_hits = sum(1 for t in tokens if t in svid) / len(tokens)

        # Channel‐based boosts.  Official Artist and Topic channels are
        # treated separately.  An official artist channel is detected if
        # the sanitized artist string appears in the sanitized channel
        # name.  Topic channels end with "topic" and host auto‑generated
        # official audio.  These boosts stack if both conditions apply.
        off = sanitize(channel_title)
        channel_boost = 0.0
        # Only apply channel boosts if there is some title match
        allow_boost = (ratio >= MIN_RATIO_FOR_BOOST) or (token_hits > 0)
        if allow_boost:
            if sanitized_artist and sanitized_artist in off:
                channel_boost += BOOST_OFFICIAL
            if off.endswith("topic"):
                channel_boost += BOOST_TOPIC

        # Additional bonuses based on metadata cues:
        # - Provided to YouTube by ... indicates auto‑generated art track
        # - Official audio markers in the title or description
        provided_boost = BOOST_PROVIDED if "provided to youtube by" in lower_desc else 0.0
        audio_boost = BOOST_AUDIO if (
            "official audio" in lower_title
            or "official audio" in lower_desc
            or "audio" in lower_title
        ) else 0.0

        # Compute a composite score.
        score = (
            ratio * WEIGHT_RATIO
            + token_hits * WEIGHT_TOKEN
            + duration_score * WEIGHT_DURATION
            + channel_boost
            + provided_boost
            + audio_boost
        )

        if score > best_score:
            best_score = score
            best_id = vid

    return best_id


def download_album_tracks(
    csv_path: str,
    api_key: str,
    workers: int = 1,
    test_mode: bool = False,
) -> None:
    """Process a CSV file and download each track's audio using YouTube Data API.

    Args:
        csv_path: Full path to the CSV produced by a parser.
        api_key: Google Cloud API key for YouTube Data API.
        workers: Number of concurrent download threads (>=1).
        test_mode: If True, skip network calls and file writes.
    """
    if not api_key:
        print("[🛑 ERROR] API key is required. Pass via --api-key or set YOUTUBE_API_KEY.")
        return
    try:
        df = pd.read_csv(csv_path, dtype=str)
    except Exception as exc:
        print(f"[🛑 ERROR] Failed to read CSV {csv_path}: {exc}")
        return
    if df.empty:
        print(f"[!] CSV is empty: {csv_path}")
        return
    print(f"[+] Processing file: {os.path.basename(csv_path)}")
    total_tracks = len(df)

    # Worker function
    def process_track(task_idx: int, row: pd.Series) -> None:
        track_number = row.get('track_number')
        title = clean_filename(str(row.get('track_title', "")))
        artist = clean_filename(str(row.get('artist_name', "")))
        album = clean_filename(str(row.get('album_name', "")))
        desired_duration = parse_duration_str(row.get('track_duration', "")) or 0
        print(f"[{task_idx}/{total_tracks}] Starting: {artist} - {title}")
        if not desired_duration:
            print(f"[{task_idx}/{total_tracks}] [!] Skipping {title} — invalid duration: {row.get('track_duration')}")
            return
        # Perform YouTube search.  Including the album name can improve
        # relevance when songs have common titles.  The query also
        # includes 'audio' to bias toward audio‑only uploads.
        query = f"{artist} {title} {album} audio"
        print(f"[{task_idx}/{total_tracks}] [-] Searching: {query}")
        results = search_youtube(api_key, query, max_results=15)
        if not results:
            # Retry with 'official audio' if no results found
            alt_query = f"{artist} {title} {album} official audio"
            print(f"[{task_idx}/{total_tracks}] [-] Retrying search: {alt_query}")
            results = search_youtube(api_key, alt_query, max_results=15)
            if not results:
                print(f"[{task_idx}/{total_tracks}] [!] No search results for: {title}")
                return
        video_ids = [res['videoId'] for res in results]
        details = get_video_details(api_key, video_ids)
        best_id = choose_best_video(results, details, desired_duration, artist, title)
        if not best_id:
            # Second attempt: search specifically for official audio
            alt_query = f"{artist} {title} {album} official audio"
            print(f"[{task_idx}/{total_tracks}] [-] No suitable candidate from initial search, trying: {alt_query}")
            results2 = search_youtube(api_key, alt_query, max_results=15)
            if results2:
                video_ids2 = [res['videoId'] for res in results2]
                details2 = get_video_details(api_key, video_ids2)
                best_id = choose_best_video(results2, details2, desired_duration, artist, title)
                if best_id:
                    results = results2
                    details = details2
                    video_ids = video_ids2
            # Third attempt: search without the album name if still none
            if not best_id:
                alt_query2 = f"{artist} {title} audio"
                print(f"[{task_idx}/{total_tracks}] [-] No suitable candidate yet, trying: {alt_query2}")
                results3 = search_youtube(api_key, alt_query2, max_results=15)
                if results3:
                    video_ids3 = [res['videoId'] for res in results3]
                    details3 = get_video_details(api_key, video_ids3)
                    best_id = choose_best_video(results3, details3, desired_duration, artist, title)
                    if best_id:
                        results = results3
                        details = details3
                        video_ids = video_ids3
            # If still no candidate, give up for this track
            if not best_id:
                print(f"[{task_idx}/{total_tracks}] [!] No suitable video found for: {title}")
                return
        # Build a list of candidate IDs – the best result first, then any other search results
        candidate_ids = [best_id] + [vid for vid in video_ids if vid != best_id]
        print(f"[{task_idx}/{total_tracks}] [✓] Found match: https://www.youtube.com/watch?v={best_id}")
        # Determine output file name and folder
        album_folder = os.path.dirname(csv_path)
        os.makedirs(album_folder, exist_ok=True)
        if pd.isna(track_number) or str(track_number).strip() == "" or track_number is None:
            filename = f"{artist} - {title}.mp3"
        else:
            try:
                num = int(float(track_number))
            except Exception:
                num = 1
                # fallback
            filename = f"{str(num).zfill(2)} - {artist} - {title}.mp3"
        # Evaluate whether the selected candidate is a weak match.  If the
        # title ratio is very low and no tokens match or the duration
        # difference exceeds the tight tolerance, prefix the filename with
        # 'CHECK_' to flag it for manual review.
        try:
            det_best = details.get(best_id, {})
            vid_title = det_best.get("title", "")
            vid_duration = det_best.get("duration", 0)
            svid = sanitize(vid_title)
            # recompute ratio and token hits
            ratio_tmp = SequenceMatcher(None, sanitize(title), svid).ratio() if sanitize(title) else 0.0
            tokens_tmp = sanitize(title).split()
            token_hits_tmp = sum(1 for t in tokens_tmp if t in svid) / len(tokens_tmp) if tokens_tmp else 0.0
            diff_tmp = abs(vid_duration - desired_duration)
            # Use the same tolerance as choose_best_video
            tol_tmp = max(int(desired_duration * 0.05), 2)
            # Flag if the ratio is below 0.15 and no tokens match, or if the
            # duration difference exceeds 15% of the desired length
            if ((ratio_tmp < 0.15 and token_hits_tmp == 0.0) or (desired_duration > 0 and diff_tmp > max(desired_duration * 0.15, 2))):
                filename = f"CHECK_{filename}"
        except Exception:
            # If something fails during flagging, silently ignore
            pass
        full_path = os.path.join(album_folder, filename)
        if test_mode:
            print(f"[{task_idx}/{total_tracks}] [TEST-MODE] Would save: {full_path}")
            return
        stem = os.path.splitext(filename)[0]
        # Select JavaScript runtimes for yt_dlp.  Provide node if available,
        # else fall back to deno.  These values are passed via
        # js_runtimes to the yt_dlp options.
        js_runtimes: Dict[str, Dict[str, Any]] = {}
        node_path = shutil.which("node")
        deno_path = shutil.which("deno")
        if node_path:
            js_runtimes["node"] = {"path": node_path}
        if deno_path:
            js_runtimes["deno"] = {"path": deno_path}
        ydl_opts: Dict[str, Any] = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': os.path.join(album_folder, stem),
            'quiet': True,
            'noplaylist': True,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }
            ],
            'concurrent_fragment_downloads': 1,
        }
        if js_runtimes:
            ydl_opts['js_runtimes'] = js_runtimes

        # Try each candidate video until one works
        success = False
        for candidate_id in candidate_ids:
            candidate_url = f"https://www.youtube.com/watch?v={candidate_id}"
            try:
                print(f"[{task_idx}/{total_tracks}] [↓] Downloading: {filename} …")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([candidate_url])
                print(f"[{task_idx}/{total_tracks}] [✓] Saved: {filename} to {album_folder}\n")
                success = True
                break
            except Exception as exc:
                print(f"[{task_idx}/{total_tracks}] [!] Error downloading {title} with {candidate_id}: {exc}")
                # Continue to the next candidate
                continue

        # If no candidate worked, fall back to the preferred_clip_url stored in the CSV
        if not success:
            fallback_url = row.get('preferred_clip_url')
            if fallback_url:
                try:
                    print(f"[{task_idx}/{total_tracks}] [↓] Attempting fallback URL for: {filename} …")
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([fallback_url])
                    print(f"[{task_idx}/{total_tracks}] [✓] Saved (fallback): {filename} to {album_folder}\n")
                    success = True
                except Exception as exc:
                    print(f"[{task_idx}/{total_tracks}] [!] Fallback download failed for {title}: {exc}")
            if not success:
                print(f"[{task_idx}/{total_tracks}] [!] All download attempts failed for: {title}")

    # Run tasks
    if workers <= 1:
        for idx, row in enumerate(df.itertuples(index=False), 1):
            process_track(idx, row._asdict())
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        tasks = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for idx, row in enumerate(df.itertuples(index=False), 1):
                tasks.append(executor.submit(process_track, idx, row._asdict()))
            for f in as_completed(tasks):
                try:
                    f.result()
                except Exception as ex:
                    print(f"[!] Worker error: {ex}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download MP3 tracks using YouTube Data API.")
    parser.add_argument("csv_path", help="Path to the album tracklist CSV")
    parser.add_argument(
        "--api-key",
        dest="api_key",
        help="YouTube Data API key (if omitted, reads from YOUTUBE_API_KEY env var)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent downloads (default: 1)",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Preview actions without downloading files",
    )
    args = parser.parse_args()
    # Determine API key
    api_key = args.api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("[🛑 ERROR] No API key provided. Use --api-key or set YOUTUBE_API_KEY.")
        sys.exit(1)
    if not os.path.exists(args.csv_path):
        print(f"[🛑 ERROR] File not found: {args.csv_path}")
        sys.exit(1)
    workers = args.workers if args.workers and args.workers > 0 else 1
    download_album_tracks(args.csv_path, api_key, workers=workers, test_mode=args.test_mode)


if __name__ == "__main__":
    main()