from __future__ import annotations

from dataclasses import dataclass

from metube_srt_desktop.domain.jobs import SourceKind
from metube_srt_desktop.domain.subtitles import SubtitleTrack


@dataclass(frozen=True, slots=True)
class ResolveRequest:
    source_url: str

    def __post_init__(self) -> None:
        if not self.source_url.strip():
            raise ValueError("source_url must be non-empty")


@dataclass(frozen=True, slots=True)
class ResolvedItem:
    video_id: str
    title: str
    webpage_url: str
    subtitles: tuple[SubtitleTrack, ...] = ()

    def __post_init__(self) -> None:
        if not self.video_id.strip():
            raise ValueError("video_id must be non-empty")
        if not self.title.strip():
            raise ValueError("title must be non-empty")
        if not self.webpage_url.strip():
            raise ValueError("webpage_url must be non-empty")


@dataclass(frozen=True, slots=True)
class ResolvedSource:
    source_url: str
    kind: SourceKind
    title: str
    items: tuple[ResolvedItem, ...]

    def __post_init__(self) -> None:
        if not self.source_url.strip():
            raise ValueError("source_url must be non-empty")
        if not self.title.strip():
            raise ValueError("title must be non-empty")
        if not self.items:
            raise ValueError("resolved source must contain at least one item")

        if self.kind is SourceKind.VIDEO and len(self.items) != 1:
            raise ValueError("video source must contain exactly one item")
