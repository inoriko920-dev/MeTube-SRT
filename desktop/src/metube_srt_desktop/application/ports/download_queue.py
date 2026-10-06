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
