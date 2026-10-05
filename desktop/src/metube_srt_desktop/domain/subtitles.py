from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class SubtitleKind(StrEnum):
    MANUAL = "manual"
    AUTO_GENERATED = "auto_generated"


@dataclass(frozen=True, slots=True)
class SubtitleTrack:
    language_code: str
    kind: SubtitleKind
    is_original: bool
    is_translated: bool = False

    def __post_init__(self) -> None:
        if not self.language_code.strip():
            raise ValueError("language_code must be non-empty")


def select_subtitle(tracks: Iterable[SubtitleTrack], *, requested: bool) -> SubtitleTrack | None:
    """Apply the frozen subtitle policy without translating or guessing.

    Priority:
    1. original creator/manual subtitle;
    2. any non-translated creator/manual subtitle;
    3. proven original auto-generated caption;
    4. no subtitle.
    """

    if not requested:
        return None

    available = tuple(track for track in tracks if not track.is_translated)

    for track in available:
        if track.kind is SubtitleKind.MANUAL and track.is_original:
            return track

    for track in available:
        if track.kind is SubtitleKind.MANUAL:
            return track

    for track in available:
        if track.kind is SubtitleKind.AUTO_GENERATED and track.is_original:
            return track

    return None
