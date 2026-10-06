from __future__ import annotations

from scripts import qualify_live_ytdlp as qualification


def test_live_qualification_defaults_cover_distinct_required_paths() -> None:
    assert qualification.DEFAULT_SINGLE_URL.startswith("https://www.youtube.com/watch?v=")
    assert qualification.DEFAULT_SRT_URL.startswith("https://www.youtube.com/watch?v=")
    assert qualification.DEFAULT_SINGLE_URL != qualification.DEFAULT_SRT_URL
    assert "playlist?list=" in qualification.DEFAULT_PLAYLIST_URL
    assert "/@" in qualification.DEFAULT_CHANNEL_URL
    assert qualification.DEFAULT_CANCEL_URL != qualification.DEFAULT_SINGLE_URL
    assert qualification.DEFAULT_FAILURE_URL.startswith("https://www.youtube.com/watch?v=")
