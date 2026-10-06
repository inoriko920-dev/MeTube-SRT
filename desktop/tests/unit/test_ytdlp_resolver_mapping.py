from __future__ import annotations

import pytest

from metube_srt_desktop.application.dto.download import ResolveRequest
from metube_srt_desktop.domain.jobs import SourceKind
from metube_srt_desktop.domain.subtitles import SubtitleKind
from metube_srt_desktop.worker.yt_dlp_resolver import is_collection_url, map_resolved_source


def _valid_item(video_id: str = "abc") -> dict[str, object]:
    return {
        "id": video_id,
        "title": f"Video {video_id}",
        "webpage_url": f"https://www.youtube.com/watch?v={video_id}",
        "extractor_key": "Youtube",
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


def test_nested_channel_maps_unique_leaf_videos_and_keeps_leaf_subtitles() -> None:
    request = ResolveRequest("https://www.youtube.com/@creator")
    manual = _valid_item("manual")
    manual["subtitles"] = {"id": [{"ext": "vtt"}]}

    automatic = _valid_item("automatic")
    automatic["automatic_captions"] = {"en-orig": [{"ext": "vtt"}]}

    none = _valid_item("none")
    raw: dict[str, object] = {
        "title": "Creator",
        "entries": [
            {
                "_type": "playlist",
                "id": "videos",
                "title": "Videos",
                "webpage_url": "https://www.youtube.com/@creator/videos",
                "entries": [manual, none],
            },
            {
                "_type": "playlist",
                "id": "shorts",
                "title": "Shorts",
                "entries": [automatic],
            },
            {
                "_type": "playlist",
                "id": "streams",
                "title": "Streams",
                "webpage_url": "https://www.youtube.com/@creator/streams",
                "entries": [manual],
            },
        ],
    }

    source = map_resolved_source(request, raw)

    assert source.kind is SourceKind.CHANNEL
    assert [item.video_id for item in source.items] == ["manual", "none", "automatic"]
    assert [item.webpage_url for item in source.items] == [
        "https://www.youtube.com/watch?v=manual",
        "https://www.youtube.com/watch?v=none",
        "https://www.youtube.com/watch?v=automatic",
    ]
    assert source.items[0].subtitles[0].kind is SubtitleKind.MANUAL
    assert source.items[1].subtitles == ()
    assert source.items[2].subtitles[0].kind is SubtitleKind.AUTO_GENERATED


def test_collection_parent_without_webpage_url_still_yields_leaf_video() -> None:
    request = ResolveRequest("https://www.youtube.com/@creator")
    raw: dict[str, object] = {
        "title": "Creator",
        "entries": [
            {
                "_type": "playlist",
                "id": "videos",
                "title": "Videos",
                "entries": [_valid_item("leaf")],
            }
        ],
    }

    source = map_resolved_source(request, raw)

    assert [item.video_id for item in source.items] == ["leaf"]


def test_collection_depth_limit_fails_clearly() -> None:
    request = ResolveRequest("https://www.youtube.com/@creator")
    nested: object = [_valid_item("leaf")]
    for index in range(10):
        nested = [
            {
                "_type": "playlist",
                "id": f"level-{index}",
                "title": f"Level {index}",
                "entries": nested,
            }
        ]

    raw: dict[str, object] = {"title": "Creator", "entries": nested}

    with pytest.raises(ValueError, match="maximum nesting depth"):
        map_resolved_source(request, raw)


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


def test_watch_url_with_playlist_context_remains_single_video() -> None:
    assert (
        is_collection_url("https://www.youtube.com/watch?v=abc123&list=PL1234567890&index=2")
        is False
    )
    assert is_collection_url("https://youtu.be/abc123?list=PL1234567890") is False
    assert is_collection_url("https://www.youtube.com/playlist?list=PL1234567890") is True
