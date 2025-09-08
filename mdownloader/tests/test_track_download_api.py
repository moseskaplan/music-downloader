# mdownloader/tests/test_track_download_api.py

import os
import pytest
import requests
from unittest.mock import patch

import mdownloader.services.track_download as td


def test_iso8601_duration_to_seconds():
    assert td.iso8601_duration_to_seconds("PT3M15S") == 195
    assert td.iso8601_duration_to_seconds("PT1H1M1S") == 3661
    assert td.iso8601_duration_to_seconds("") == 0


@patch("requests.get")
def test_search_youtube_returns_results(mock_get):
    # Mock API JSON response
    mock_get.return_value.json.return_value = {
        "items": [
            {"id": {"videoId": "abc123"},
             "snippet": {"title": "Test Song", "channelTitle": "Artist - Topic"}}
        ]
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = lambda: None

    results = td.search_youtube("fake_api_key", "Test Song", max_results=1)
    assert isinstance(results, list)
    assert results[0]["videoId"] == "abc123"
    assert "title" in results[0]


@patch("requests.get")
def test_get_video_details_returns_metadata(mock_get):
    mock_get.return_value.json.return_value = {
        "items": [
            {"id": "abc123",
             "snippet": {"title": "Test Song", "channelTitle": "Artist - Topic"},
             "contentDetails": {"duration": "PT3M15S"}}
        ]
    }
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = lambda: None

    details = td.get_video_details("fake_api_key", ["abc123"])
    assert "abc123" in details
    assert details["abc123"]["duration"] == 195
    assert details["abc123"]["title"] == "Test Song"


def test_choose_best_video_prefers_official_channel():
    candidates = [
        {"videoId": "vid1", "title": "Song X", "channelTitle": "Random Guy"},
        {"videoId": "vid2", "title": "Song X (Official Audio)", "channelTitle": "Artist - Topic"},
    ]
    details = {
        "vid1": {"duration": 180, "title": "Song X", "channelTitle": "Random Guy"},
        "vid2": {"duration": 182, "title": "Song X (Official Audio)", "channelTitle": "Artist - Topic"},
    }
    best = td.choose_best_video(candidates, details, desired_duration=180, artist="Artist", title="Song X")
    assert best == "vid2"


def test_download_album_tracks_missing_api_key(monkeypatch, tmp_path):
    # Remove key from environment
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)

    csv_path = tmp_path / "tracks.csv"
    csv_path.write_text("track_number,track_title,artist_name,album_name,track_duration\n"
                        "1,Test Song,Artist,Album,3:00\n")

    # Should early-exit with clear error
    td.download_album_tracks(str(csv_path), api_key=None, workers=1, test_mode=True)