import pytest

from metube_srt_desktop.application.dto.download import ResolveRequest
from metube_srt_desktop.domain.jobs import SourceKind
from metube_srt_desktop.domain.subtitles import SubtitleKind, select_subtitle
from metube_srt_desktop.worker.yt_dlp_resolver import map_resolved_source


def video_info() -> dict[str, object]:
    return {
        "id": "abc123",
        "title": "Video",
        "webpage_url": "https://www.youtube.com/watch?v=abc123",
        "subtitles": {
            "en": [{"ext": "vtt"}],
            "live_chat": [{"ext": "json"}],
        },
        "automatic_captions": {
            "id-orig": [{"ext": "vtt"}],
            "en": [{"ext": "vtt"}],
            "de": [{"ext": "vtt"}],
        },
    }


def test_single_video_maps_manual_and_only_proven_original_auto_caption() -> None:
    resolved = map_resolved_source(
        ResolveRequest("https://www.youtube.com/watch?v=abc123"),
        video_info(),
    )

    assert resolved.kind is SourceKind.VIDEO
    assert len(resolved.items) == 1
    tracks = resolved.items[0].subtitles
    assert [(track.language_code, track.kind, track.is_original) for track in tracks] == [
        ("en", SubtitleKind.MANUAL, False),
        ("id-orig", SubtitleKind.AUTO_GENERATED, True),
    ]
    assert select_subtitle(tracks, requested=True) is tracks[0]


def test_original_auto_caption_is_selected_when_manual_track_is_absent() -> None:
    raw = video_info()
    raw["subtitles"] = {}

    resolved = map_resolved_source(
        ResolveRequest("https://www.youtube.com/watch?v=abc123"),
        raw,
    )

    selected = select_subtitle(resolved.items[0].subtitles, requested=True)
    assert selected is not None
    assert selected.language_code == "id-orig"
    assert selected.kind is SubtitleKind.AUTO_GENERATED


def test_playlist_entries_expand_to_typed_items() -> None:
    first = video_info()
    second: dict[str, object] = {
        "id": "def456",
        "title": "Video 2",
        "webpage_url": "https://www.youtube.com/watch?v=def456",
        "subtitles": {},
        "automatic_captions": {},
    }
    raw: dict[str, object] = {
        "id": "PL123",
        "title": "Playlist",
        "entries": [first, second],
    }

    resolved = map_resolved_source(
        ResolveRequest("https://www.youtube.com/playlist?list=PL123"),
        raw,
    )

    assert resolved.kind is SourceKind.PLAYLIST
    assert [item.video_id for item in resolved.items] == ["abc123", "def456"]


def test_channel_url_is_classified_without_inferring_from_title() -> None:
    raw: dict[str, object] = {
        "id": "channel",
        "title": "Channel uploads",
        "entries": [video_info()],
    }

    resolved = map_resolved_source(
        ResolveRequest("https://www.youtube.com/@creator/videos"),
        raw,
    )

    assert resolved.kind is SourceKind.CHANNEL


def test_unknown_collection_shape_is_rejected_instead_of_guessed() -> None:
    raw: dict[str, object] = {
        "id": "collection",
        "title": "Unknown collection",
        "entries": [video_info()],
    }

    with pytest.raises(ValueError, match="not a recognized YouTube playlist or channel"):
        map_resolved_source(ResolveRequest("https://www.youtube.com/feed/history"), raw)


def test_item_without_absolute_webpage_url_is_rejected() -> None:
    raw = video_info()
    raw["webpage_url"] = "abc123"

    with pytest.raises(ValueError, match="absolute webpage URL"):
        map_resolved_source(
            ResolveRequest("https://www.youtube.com/watch?v=abc123"),
            raw,
        )
