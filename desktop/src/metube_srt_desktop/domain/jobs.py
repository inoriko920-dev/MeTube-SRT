from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlsplit

from metube_srt_desktop.domain.subtitles import SubtitleTrack


class SourceKind(StrEnum):
    VIDEO = "video"
    PLAYLIST = "playlist"
    CHANNEL = "channel"


class JobState(StrEnum):
    QUEUED = "queued"
    RESOLVING = "resolving"
    RUNNING = "running"
    POSTPROCESSING = "postprocessing"
    CANCELLING = "cancelling"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


_TERMINAL_JOB_STATES = {
    JobState.SUCCEEDED,
    JobState.FAILED,
    JobState.CANCELLED,
    JobState.INTERRUPTED,
}

_ALLOWED_JOB_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.QUEUED: frozenset(
        {
            JobState.RESOLVING,
            JobState.RUNNING,
            JobState.CANCELLING,
            JobState.CANCELLED,
            JobState.INTERRUPTED,
        }
    ),
    JobState.RESOLVING: frozenset(
        {
            JobState.RUNNING,
            JobState.CANCELLING,
            JobState.FAILED,
            JobState.CANCELLED,
            JobState.INTERRUPTED,
        }
    ),
    JobState.RUNNING: frozenset(
        {
            JobState.POSTPROCESSING,
            JobState.CANCELLING,
            JobState.SUCCEEDED,
            JobState.FAILED,
            JobState.CANCELLED,
            JobState.INTERRUPTED,
        }
    ),
    JobState.POSTPROCESSING: frozenset(
        {
            JobState.CANCELLING,
            JobState.SUCCEEDED,
            JobState.FAILED,
            JobState.CANCELLED,
            JobState.INTERRUPTED,
        }
    ),
    JobState.CANCELLING: frozenset(
        {
            JobState.SUCCEEDED,
            JobState.FAILED,
            JobState.CANCELLED,
            JobState.INTERRUPTED,
        }
    ),
    JobState.SUCCEEDED: frozenset(),
    JobState.FAILED: frozenset(),
    JobState.CANCELLED: frozenset(),
    JobState.INTERRUPTED: frozenset(),
}


def is_terminal_job_state(state: JobState) -> bool:
    return state in _TERMINAL_JOB_STATES


def transition_job_state(current: JobState, target: JobState) -> JobState:
    """Validate one canonical job-state transition."""

    if current is target:
        return current
    if target not in _ALLOWED_JOB_TRANSITIONS[current]:
        raise ValueError(f"invalid job state transition: {current.value} -> {target.value}")
    return target


class QualityPreset(StrEnum):
    BEST = "best"
    P1080 = "1080p"
    P720 = "720p"
    P480 = "480p"


@dataclass(frozen=True, slots=True)
class JobSpec:
    job_id: str
    source_url: str
    output_directory: str
    quality: QualityPreset
    selected_subtitle: SubtitleTrack | None

    def __post_init__(self) -> None:
        if not self.job_id.strip():
            raise ValueError("job_id must be non-empty")
        if not self.output_directory.strip():
            raise ValueError("output_directory must be non-empty")

        parsed = urlsplit(self.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("source_url must be an absolute http(s) URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("source_url must not contain embedded credentials")
