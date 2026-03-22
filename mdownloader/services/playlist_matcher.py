"""Fuzzy-match a YouTube playlist against an album track list.

Uses rapidfuzz token_sort_ratio so word-order differences (e.g. leading
track numbers or 'Remastered' suffixes) don't kill the score.
Each playlist entry is assigned to at most one album row (greedy, best-first).
"""

from rapidfuzz import process, fuzz

MATCH_THRESHOLD = 70  # minimum score (0–100) to accept a match


def match_playlist_to_tracks(
    album_tracks: list[dict],
    playlist_entries: list[dict],
    threshold: int = MATCH_THRESHOLD,
) -> dict[int, str]:
    """Match playlist entries to album tracks by title.

    Args:
        album_tracks:     list of track dicts (must have 'track_title' key).
        playlist_entries: list of {title, url} dicts from PlaylistFetchWorker.
        threshold:        minimum rapidfuzz score to accept a match.

    Returns:
        dict mapping row_index → youtube_url for every accepted match.
        Rows with no match above threshold are omitted.
        Each playlist entry is used at most once.
    """
    playlist_titles = [e["title"] for e in playlist_entries]
    assignments: dict[int, str] = {}
    used: set[int] = set()

    for row, track in enumerate(album_tracks):
        result = process.extractOne(
            track["track_title"],
            playlist_titles,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=threshold,
        )
        if result is None:
            continue
        _matched_title, _score, idx = result
        if idx in used:
            continue
        used.add(idx)
        assignments[row] = playlist_entries[idx]["url"]

    return assignments
