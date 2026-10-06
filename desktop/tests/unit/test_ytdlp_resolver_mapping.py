from __future__ import annotations

import pytest

from metube_srt_desktop.application.dto.download import ResolveRequest
from metube_srt_desktop.domain.jobs import SourceKind
from metube_srt_desktop.worker.yt_dlp_resolver import map_resolved_source


def _valid_item(video_id: str = "abc") -> dict[str, object]:
    return {
        "id": video_id,
        "title": f"Video {video_id}",
        "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
        "subtitles": {},
        "automatic_captions": {},
    }


def test_playlist_skips_unavailable_entries_instead_of_failing_all() -> None:
    request = ResolveRequest("https://www.youtube.com/playlist?list=PL1234567890")
    raw: dict[str, object] = {
        "title": "Playlist Uji",
        "entries": [
            _valid_item("available"),
            None,
            {
                "id": "private",
                "title": "Private video",
            },
            {
                "id": "deleted",
            },
        ],
    }

    source = map_resolved_source(request, raw)

    assert source.kind is SourceKind.PLAYLIST
    assert [item.video_id for item in source.items] == ["available"]


def test_collection_with_no_downloadable_entries_fails_clearly() -> None:
    request = ResolveRequest("https://www.youtube.com/playlist?list=PL1234567890")
    raw: dict[str, object] = {
        "title": "Playlist Kosong",
        "entries": [
            None,
            {"id": "private", "title": "Private video"},
        ],
    }

    with pytest.raises(ValueError, match="no downloadable video items"):
        map_resolved_source(request, raw)


def test_single_video_still_rejects_incomplete_metadata() -> None:
    request = ResolveRequest("https://www.youtube.com/watch?v=abc")
    raw: dict[str, object] = {
        "id": "abc",
        "title": "Video Uji",
    }

    with pytest.raises(ValueError, match="absolute webpage URL"):
        map_resolved_source(request, raw)
