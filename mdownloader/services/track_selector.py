"""Select appropriate YouTube videos for each track.

This module reads a CSV produced by one of the parser modules (e.g. the
Apple or Wikipedia parser) and uses the YouTube Data API to search for
matching videos.  It applies a heuristic scoring algorithm to choose
the best candidate for each track based on duration, title similarity,
token coverage and channel metadata.  The resulting YouTube URL is
written back into the CSV in a new column named ``selected_url``.  A
``selection_flag`` column is also added; rows flagged ``True`` should be
treated with caution when downloading (e.g. by prefixing the filename
with ``CHECK_``).  Tracks for which no suitable candidate is found will
have a blank ``selected_url`` and ``selection_flag`` set to ``True``.

Unlike the downloader, this script does not perform any downloads.  It
simply evaluates search results and populates the CSV so that
``track_download.py`` can later download the chosen URLs.  Separating
selection from downloading allows you to iterate on the heuristics
without affecting the core downloading logic and makes it easier to
integrate a GUI where users can review or override the choices.

Usage::

    python3 -m mdownloader.services.track_selector <csv_path> --api-key <KEY>

The API key argument is optional if the ``YOUTUBE_API_KEY`` environment
variable is set.  If no key is available the script will exit with an
error.  You can override the default maximum number of results to
consider by passing ``--max-results``; the default is 15.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import requests
from difflib import SequenceMatcher

from mdownloader.core.utils import parse_duration_str, clean_filename


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


def search_youtube(api_key: str, query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """Search YouTube for videos using the YouTube Data API.

    Args:
        api_key: Google Cloud API key with YouTube Data API enabled.
        query: Search query string.
        max_results: Maximum number of results to return (default 15).

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
    except Exception:
        return []
    items = data.get("items", [])
    results: List[Dict[str, Any]] = []
    for item in items:
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        title = snippet.get("title", "")
        channel_title = snippet.get("channelTitle", "")
        if video_id:
            results.append({"videoId": video_id, "title": title, "channelTitle": channel_title})
    return results


def get_video_details(api_key: str, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Retrieve video durations and metadata for a list of video IDs.

    Args:
        api_key: API key for YouTube Data API.
        video_ids: List of YouTube video IDs.

    Returns:
        A dict mapping video ID to a dict with keys ``duration`` (int
        seconds), ``channelTitle``, ``title`` and ``description``.
        Missing IDs will not appear in the output.
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
    except Exception:
        return details
    for item in data.get("items", []):
        vid = item.get("id")
        snippet = item.get("snippet", {})
        content = item.get("contentDetails", {})
        duration_iso = content.get("duration", "")
        # Convert ISO 8601 duration to seconds
        seconds = 0
        if duration_iso:
            pattern = re.compile(r"PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+)S)?")
            m = pattern.fullmatch(duration_iso)
            if m:
                hours = int(m.group("h") or 0)
                minutes = int(m.group("m") or 0)
                secs = int(m.group("s") or 0)
                seconds = hours * 3600 + minutes * 60 + secs
        details[vid] = {
            "duration": seconds,
            "channelTitle": snippet.get("channelTitle", ""),
            "title": snippet.get("title", ""),
            "description": snippet.get("description", ""),
        }
    return details


def choose_best_video(
    candidates: List[Dict[str, Any]],
    details: Dict[str, Dict[str, Any]],
    desired_duration: int,
    artist: str,
    title: str,
) -> tuple[str | None, float, float, float, float, bool]:
    """Pick the best YouTube video from search results.

    The selection algorithm uses a weighted combination of features to
    determine the most appropriate video.  Duration closeness carries
    the most weight, followed by title similarity and token coverage.
    Channels that match the artist or end with "topic" receive
    additional boosts.  Videos with lyric or cover labels are skipped.

    Args:
        candidates: List of dicts from ``search_youtube``.
        details: Mapping of video IDs to their details from
            ``get_video_details``.
        desired_duration: Target track duration in seconds.
        artist: Cleaned artist name.
        title: Cleaned track title.

    Returns:
        A tuple containing:
            - The chosen video ID (or ``None`` if none are suitable)
            - The fuzzy title ratio
            - The token coverage fraction
            - The absolute duration difference in seconds
            - The computed score
            - A boolean indicating whether this candidate should be
              flagged for manual review (True means the match is weak)
    """
    # Keywords that indicate the video is not a studio audio recording.
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

    # Weight constants for scoring components.  Duration closeness carries
    # the most weight, with title similarity and token coverage playing
    # smaller roles.  Channel and metadata cues provide additive boosts.
    WEIGHT_RATIO = 0.25
    WEIGHT_TOKEN = 0.15
    WEIGHT_DURATION = 0.45
    BOOST_TOPIC = 0.25
    BOOST_OFFICIAL = 0.15
    BOOST_PROVIDED = 0.20
    BOOST_AUDIO = 0.10

    sanitized_title = sanitize(title)
    sanitized_artist = sanitize(artist)
    tokens = sanitized_title.split()
    # Tighter tolerance for duration matching; 5% of desired duration or 2 seconds
    tolerance = max(int(desired_duration * 0.05), 2)
    best_score = 0.0
    best_id: str | None = None
    best_ratio = 0.0
    best_token_hits = 0.0
    best_diff = float("inf")
    flagged = True

    # Minimum title ratio for channel boosts; below this ratio and with no
    # token hits we ignore channel/topic boosts.
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
        if any(bad in lower_title or bad in lower_desc for bad in bad_keywords):
            continue

        # Duration filtering: discard videos whose length deviates by more than
        # 15% of the desired duration plus 2 seconds.
        dur = det.get("duration", 0)
        diff = abs(dur - desired_duration)
        if desired_duration > 0 and diff > max(desired_duration * 0.15, 2):
            continue
        duration_score = max(0.0, 1.0 - diff / tolerance)

        # Fuzzy ratio between the sanitized track title and the video title.
        svid = sanitize(video_title)
        ratio = SequenceMatcher(None, sanitized_title, svid).ratio() if sanitized_title else 0.0

        # Token coverage: fraction of tokens in the track title that appear in the video title.
        token_hits = 0.0
        if tokens:
            token_hits = sum(1 for t in tokens if t in svid) / len(tokens)

        # Channel boosts applied only if some title match exists
        channel_boost = 0.0
        allow_boost = (ratio >= MIN_RATIO_FOR_BOOST) or (token_hits > 0)
        off = sanitize(channel_title)
        if allow_boost:
            if sanitized_artist and sanitized_artist in off:
                channel_boost += BOOST_OFFICIAL
            if off.endswith("topic"):
                channel_boost += BOOST_TOPIC

        provided_boost = BOOST_PROVIDED if "provided to youtube by" in lower_desc else 0.0
        audio_boost = BOOST_AUDIO if (
            "official audio" in lower_title
            or "official audio" in lower_desc
            or "audio" in lower_title
        ) else 0.0

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
            best_ratio = ratio
            best_token_hits = token_hits
            best_diff = diff
            # Determine if this candidate is strong: good title match and close duration
            flagged = not ((ratio >= MIN_RATIO_FOR_BOOST or token_hits > 0) and (diff <= max(desired_duration * 0.15, 2)))

    return best_id, best_ratio, best_token_hits, best_diff, best_score, flagged


def select_tracks(csv_path: str, api_key: str, max_results: int = 15) -> None:
    """Populate selected_url and selection_flag columns in the given CSV.

    Reads the CSV at ``csv_path``, determines a YouTube URL for each
    track using the selection heuristic, and writes the results back
    into the same CSV.  Two new columns are added: ``selected_url``
    (the chosen YouTube link or blank if none) and ``selection_flag``
    (``True`` if the match is weak or missing; ``False`` otherwise).

    Args:
        csv_path: Path to the tracklist CSV produced by a parser.
        api_key: YouTube Data API key.
        max_results: Maximum number of search results to consider.
    """
    try:
        df = pd.read_csv(csv_path, dtype=str)
    except Exception as exc:
        print(f"[🛑 ERROR] Failed to read CSV {csv_path}: {exc}")
        return
    if df.empty:
        print(f"[!] CSV is empty: {csv_path}")
        return
    # Ensure output columns exist
    if "selected_url" not in df.columns:
        df["selected_url"] = ""
    if "selection_flag" not in df.columns:
        df["selection_flag"] = False

    # Iterate through each track and select the best video
    for idx, row in df.iterrows():
        title = clean_filename(str(row.get("track_title", "")))
        artist = clean_filename(str(row.get("artist_name", "")))
        album = clean_filename(str(row.get("album_name", "")))
        desired_duration = parse_duration_str(row.get("track_duration", "")) or 0
        if not desired_duration:
            df.at[idx, "selection_flag"] = True
            continue
        # Build search queries in order of preference
        queries = [
            f"{artist} {title} {album} audio",
            f"{artist} {title} {album} official audio",
            f"{artist} {title} audio",
        ]
        selected_url = ""
        flagged = True
        best_score = 0.0
        for q in queries:
            results = search_youtube(api_key, q, max_results=max_results)
            if not results:
                continue
            video_ids = [res["videoId"] for res in results]
            details = get_video_details(api_key, video_ids)
            best_id, ratio, token_hits, diff, score, flag = choose_best_video(
                results, details, desired_duration, artist, title
            )
            if best_id:
                selected_url = f"https://www.youtube.com/watch?v={best_id}"
                flagged = flag
                best_score = score
                break  # Stop after finding a candidate
        df.at[idx, "selected_url"] = selected_url
        df.at[idx, "selection_flag"] = bool(flagged or not selected_url)
    # Write updated CSV back to disk
    df.to_csv(csv_path, index=False)
    print(f"[✓] Selector wrote results to: {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Select best YouTube videos for each track.")
    parser.add_argument("csv_path", help="Path to the album tracklist CSV")
    parser.add_argument("--api-key", dest="api_key", help="YouTube Data API key (if omitted, reads from YOUTUBE_API_KEY env var)")
    parser.add_argument("--max-results", dest="max_results", type=int, default=15, help="Maximum number of search results to consider")
    args = parser.parse_args()
    api_key = args.api_key or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("[🛑 ERROR] No API key provided. Use --api-key or set YOUTUBE_API_KEY.")
        sys.exit(1)
    if not os.path.exists(args.csv_path):
        print(f"[🛑 ERROR] File not found: {args.csv_path}")
        sys.exit(1)
    select_tracks(args.csv_path, api_key, max_results=args.max_results)


if __name__ == "__main__":
    main()