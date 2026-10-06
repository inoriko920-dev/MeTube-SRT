from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

from metube_srt_desktop.adapters.storage import SQLiteQueueStorage
from metube_srt_desktop.application.download_planning import DownloadSelection
from metube_srt_desktop.application.download_queue import BoundedDownloadQueue
from metube_srt_desktop.application.download_submission import ResolvePlanEnqueueUseCase
from metube_srt_desktop.application.dto.download import (
    ResolvedItem,
    ResolvedSource,
    ResolveRequest,
)
from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.application.dto.worker_protocol import (
    WORKER_PROTOCOL_VERSION,
    WorkerEnvelope,
    WorkerEventType,
)
from metube_srt_desktop.application.ports.download_worker import DownloadWorkerPort
from metube_srt_desktop.application.ports.source_resolver import SourceResolveError
from metube_srt_desktop.domain.jobs import JobSpec, JobState, QualityPreset, SourceKind
from metube_srt_desktop.domain.subtitles import SubtitleKind, SubtitleTrack


class FakeResolver:
    def __init__(self, source: ResolvedSource) -> None:
        self.source = source
        self.requests: list[ResolveRequest] = []

    def resolve(self, request: ResolveRequest) -> ResolvedSource:
        self.requests.append(request)
        return self.source


class FailingResolver:
    def resolve(self, request: ResolveRequest) -> ResolvedSource:
        raise SourceResolveError("resolve_failed", "Source resolve failed")


class ImmediateWorker:
    def __init__(self, job_id: str, worker_run_id: str) -> None:
        self.job_id = job_id
        self.worker_run_id = worker_run_id

    def events(self) -> Iterable[WorkerEnvelope]:
        yield WorkerEnvelope(
            schema_version=WORKER_PROTOCOL_VERSION,
            event_type=WorkerEventType.READY,
            job_id=self.job_id,
            worker_run_id=self.worker_run_id,
            sequence=0,
            payload={},
        )
        yield WorkerEnvelope(
            schema_version=WORKER_PROTOCOL_VERSION,
            event_type=WorkerEventType.SUCCEEDED,
            job_id=self.job_id,
            worker_run_id=self.worker_run_id,
            sequence=1,
            payload={},
        )

    def request_cancel(self) -> None:
        return


class ImmediateWorkerFactory:
    def __init__(self) -> None:
        self.jobs: list[JobSpec] = []

    def create(
        self,
        job: JobSpec,
        *,
        worker_run_id: str,
    ) -> DownloadWorkerPort:
        self.jobs.append(job)
        return ImmediateWorker(job.job_id, worker_run_id)


class RejectingQueue:
    def __init__(self) -> None:
        self.calls = 0

    def enqueue_many(
        self,
        jobs: Iterable[JobSpec],
    ) -> tuple[JobRuntimeSnapshot, ...]:
        self.calls += 1
        raise AssertionError("queue must not be called")


def make_playlist() -> ResolvedSource:
    manual = SubtitleTrack(
        language_code="id",
        kind=SubtitleKind.MANUAL,
        is_original=True,
    )
    auto = SubtitleTrack(
        language_code="en-orig",
        kind=SubtitleKind.AUTO_GENERATED,
        is_original=True,
    )
    return ResolvedSource(
        source_url="https://www.youtube.com/playlist?list=PL123",
        kind=SourceKind.PLAYLIST,
        title="Playlist",
        items=(
            ResolvedItem(
                video_id="a",
                title="A",
                webpage_url="https://www.youtube.com/watch?v=a",
                subtitles=(manual,),
            ),
            ResolvedItem(
                video_id="b",
                title="B",
                webpage_url="https://www.youtube.com/watch?v=b",
                subtitles=(auto,),
            ),
        ),
    )


def test_resolve_plan_enqueue_persists_per_video_jobs(tmp_path: Path) -> None:
    source = make_playlist()
    resolver = FakeResolver(source)
    storage = SQLiteQueueStorage(tmp_path / "app.db")
    worker_factory = ImmediateWorkerFactory()
    queue = BoundedDownloadQueue(
        worker_factory,
        concurrency=2,
        worker_run_id_factory=iter(("run-a", "run-b")).__next__,
        storage=storage,
    )
    use_case = ResolvePlanEnqueueUseCase(
        resolver,
        queue,
        job_id_factory=iter(("job-a", "job-b")).__next__,
    )

    result = use_case.execute(
        ResolveRequest(source.source_url),
        DownloadSelection(
            output_directory="Downloads",
            quality=QualityPreset.P1080,
            subtitle_requested=True,
        ),
    )
    queue.shutdown(wait=True)

    assert resolver.requests == [ResolveRequest(source.source_url)]
    assert [job.job_id for job in result.jobs] == ["job-a", "job-b"]
    assert [
        job.selected_subtitle.language_code for job in result.jobs if job.selected_subtitle
    ] == [
        "id",
        "en-orig",
    ]
    assert [snapshot.job_id for snapshot in result.queued] == ["job-a", "job-b"]
    assert [snapshot.state for snapshot in queue.snapshots()] == [
        JobState.SUCCEEDED,
        JobState.SUCCEEDED,
    ]

    persisted = storage.load_entries()
    assert [entry.job.job_id for entry in persisted] == ["job-a", "job-b"]
    assert all(entry.job.quality is QualityPreset.P1080 for entry in persisted)
    assert all(entry.snapshot.state is JobState.SUCCEEDED for entry in persisted)


def test_resolve_failure_never_reaches_planning_or_queue() -> None:
    queue = RejectingQueue()
    use_case = ResolvePlanEnqueueUseCase(
        FailingResolver(),
        queue,
        job_id_factory=lambda: "job-never-used",
    )

    with pytest.raises(SourceResolveError, match="Source resolve failed"):
        use_case.execute(
            ResolveRequest("https://www.youtube.com/watch?v=abc"),
            DownloadSelection(
                output_directory="Downloads",
                quality=QualityPreset.BEST,
                subtitle_requested=False,
            ),
        )

    assert queue.calls == 0
