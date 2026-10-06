from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.domain.jobs import JobSpec


class DownloadQueuePort(Protocol):
    """Application-owned command boundary for admitting planned download jobs."""

    def enqueue_many(
        self,
        jobs: Iterable[JobSpec],
    ) -> tuple[JobRuntimeSnapshot, ...]: ...


class QueueRuntimePort(DownloadQueuePort, Protocol):
    """Presentation-facing application boundary for queue state and cancellation."""

    def cancel(self, job_id: str) -> JobRuntimeSnapshot: ...

    def snapshots(self) -> tuple[JobRuntimeSnapshot, ...]: ...

    def drain_updates(self) -> tuple[JobRuntimeSnapshot, ...]: ...

    def job_specs(self) -> tuple[JobSpec, ...]: ...
