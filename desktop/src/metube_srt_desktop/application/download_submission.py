from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from metube_srt_desktop.application.download_planning import (
    DownloadSelection,
    plan_download_jobs,
)
from metube_srt_desktop.application.dto.download import ResolvedSource, ResolveRequest
from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.application.ports.download_queue import DownloadQueuePort
from metube_srt_desktop.application.ports.source_resolver import SourceResolverPort
from metube_srt_desktop.domain.jobs import JobSpec


def _new_job_id() -> str:
    return uuid4().hex


@dataclass(frozen=True, slots=True)
class DownloadSubmissionResult:
    source: ResolvedSource
    jobs: tuple[JobSpec, ...]
    queued: tuple[JobRuntimeSnapshot, ...]

    def __post_init__(self) -> None:
        if len(self.jobs) != len(self.queued):
            raise ValueError("planned jobs and queued snapshots must have the same length")
        for job, snapshot in zip(self.jobs, self.queued, strict=True):
            if job.job_id != snapshot.job_id:
                raise ValueError("queued snapshot does not match its planned job")


class ResolvePlanEnqueueUseCase:
    """Resolve one source, freeze per-video jobs, then admit them to the queue."""

    def __init__(
        self,
        resolver: SourceResolverPort,
        queue: DownloadQueuePort,
        *,
        job_id_factory: Callable[[], str] = _new_job_id,
    ) -> None:
        self._resolver = resolver
        self._queue = queue
        self._job_id_factory = job_id_factory

    def execute(
        self,
        request: ResolveRequest,
        selection: DownloadSelection,
    ) -> DownloadSubmissionResult:
        source = self._resolver.resolve(request)
        jobs = plan_download_jobs(
            source,
            selection,
            job_id_factory=self._job_id_factory,
        )
        queued = self._queue.enqueue_many(jobs)
        return DownloadSubmissionResult(
            source=source,
            jobs=jobs,
            queued=queued,
        )
