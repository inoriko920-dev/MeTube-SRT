from __future__ import annotations

from dataclasses import dataclass

from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.domain.jobs import JobSpec


@dataclass(frozen=True, slots=True)
class PersistedQueueEntry:
    position: int
    job: JobSpec
    snapshot: JobRuntimeSnapshot

    def __post_init__(self) -> None:
        if self.position < 0:
            raise ValueError("position must be >= 0")
        if self.job.job_id != self.snapshot.job_id:
            raise ValueError("persisted job and snapshot must share job_id")
