from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast
from urllib.parse import parse_qs, urlsplit

from metube_srt_desktop.application.dto.download import (
    ResolvedItem,
    ResolvedSource,
    ResolveRequest,
)
from metube_srt_desktop.domain.jobs import SourceKind
from metube_srt_desktop.domain.subtitles import SubtitleKind, SubtitleTrack

_ORIGINAL_AUTO_SUFFIX = "-orig"
_CHANNEL_PREFIXES = ("/@", "/channel/", "/c/", "/user/")


def map_resolved_source(request: ResolveRequest, raw_info: Mapping[str, object]) -> ResolvedSource:
    """Map sanitized yt-dlp metadata to the application-owned resolve DTO."""

    raw_entries = raw_info.get("entries")
    if _is_entry_sequence(raw_entries):
        kind = _classify_collection_url(request.source_url)
        items = _map_collection_items(raw_entries)
        if not items:
            raise ValueError("resolved collection contains no downloadable video items")
    else:
        kind = SourceKind.VIDEO
        items = (_map_item(raw_info),)

    title = _required_string(raw_info, "title")
    return ResolvedSource(
        source_url=request.source_url,
        kind=kind,
        title=title,
        items=items,
    )


def _map_item(raw_info: Mapping[str, object]) -> ResolvedItem:
    return ResolvedItem(
        video_id=_required_string(raw_info, "id"),
        title=_required_string(raw_info, "title"),
        webpage_url=_required_absolute_url(raw_info),
        subtitles=_extract_subtitle_tracks(raw_info),
    )


def _extract_subtitle_tracks(raw_info: Mapping[str, object]) -> tuple[SubtitleTrack, ...]:
    tracks: list[SubtitleTrack] = []

    for language_code in _mapping_keys(raw_info.get("subtitles")):
        if language_code == "live_chat":
            continue
        tracks.append(
            SubtitleTrack(
                language_code=language_code,
                kind=SubtitleKind.MANUAL,
                is_original=False,
            )
        )

    for language_code in _mapping_keys(raw_info.get("automatic_captions")):
        if not language_code.endswith(_ORIGINAL_AUTO_SUFFIX):
            continue
        tracks.append(
            SubtitleTrack(
                language_code=language_code,
                kind=SubtitleKind.AUTO_GENERATED,
                is_original=True,
            )
        )

    return tuple(tracks)


def _classify_collection_url(source_url: str) -> SourceKind:
    parsed = urlsplit(source_url)
    query = parse_qs(parsed.query)
    if "list" in query or parsed.path.rstrip("/") == "/playlist":
        return SourceKind.PLAYLIST
    if parsed.path.startswith(_CHANNEL_PREFIXES):
        return SourceKind.CHANNEL
    raise ValueError("resolved collection URL is not a recognized YouTube playlist or channel")


def _required_absolute_url(raw_info: Mapping[str, object]) -> str:
    for key in ("webpage_url", "original_url"):
        candidate = raw_info.get(key)
        if isinstance(candidate, str):
            parsed = urlsplit(candidate)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                return candidate
    raise ValueError("resolved video item is missing an absolute webpage URL")


def _required_string(raw_info: Mapping[str, object], key: str) -> str:
    value = raw_info.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"resolved metadata field {key!r} must be a non-empty string")
    return value


def _is_entry_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _map_collection_items(value: object) -> tuple[ResolvedItem, ...]:
    if not _is_entry_sequence(value):
        return ()

    items: list[ResolvedItem] = []
    for entry in cast(Sequence[object], value):
        if not isinstance(entry, Mapping):
            continue
        try:
            items.append(_map_item(cast(Mapping[str, object], entry)))
        except ValueError:
            # Deleted/private/unavailable playlist entries can have partial metadata.
            continue
    return tuple(items)


def _mapping_keys(value: object) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        return ()
    mapping = cast(Mapping[object, object], value)
    return tuple(key for key in mapping if isinstance(key, str) and key.strip())
