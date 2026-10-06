from __future__ import annotations

from collections.abc import Iterable
from threading import Condition, Event, Lock

import pytest

from metube_srt_desktop.application.download_queue import BoundedDownloadQueue
from metube_srt_desktop.application.dto.worker_protocol import (
    WORKER_PROTOCOL_VERSION,
    WorkerEnvelope,
    WorkerEventType,
)
from metube_srt_desktop.application.ports.download_worker import (
    DownloadWorkerError,
    DownloadWorkerPort,
)
from metube_srt_desktop.domain.jobs import JobSpec, JobState, QualityPreset


class ActivityMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self.active = 0
        self.peak = 0

    def enter(self) -> None:
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)

    def leave(self) -> None:
        with self._lock:
            self.active -= 1


class GateWorker:
    def __init__(
        self,
        job_id: str,
        worker_run_id: str,
        metrics: ActivityMetrics,
    ) -> None:
        self.job_id = job_id
        self.worker_run_id = worker_run_id
        self.metrics = metrics
        self.started = Event()
        self.done = Event()
        self.cancelled = Event()
        self.cancel_requests = 0

    def events(self) -> Iterable[WorkerEnvelope]:
        self.metrics.enter()
        self.started.set()
        yield self._event(WorkerEventType.READY, 0)
        if not self.done.wait(2.0):
            self.metrics.leave()
            raise DownloadWorkerError("test worker timed out")
        self.metrics.leave()
        if self.cancelled.is_set():
            yield self._event(WorkerEventType.CANCELLED, 1)
        else:
            yield self._event(WorkerEventType.SUCCEEDED, 1)

    def request_cancel(self) -> None:
        self.cancel_requests += 1
        self.cancelled.set()
        self.done.set()

    def release(self) -> None:
        self.done.set()

    def _event(self, event_type: WorkerEventType, sequence: int) -> WorkerEnvelope:
        return WorkerEnvelope(
            schema_version=WORKER_PROTOCOL_VERSION,
            event_type=event_type,
            job_id=self.job_id,
            worker_run_id=self.worker_run_id,
            sequence=sequence,
            payload={},
        )


class BlockingWorkerFactory:
    def __init__(self) -> None:
        self.metrics = ActivityMetrics()
        self._condition = Condition()
        self.created: list[str] = []
        self.workers: dict[str, GateWorker] = {}

    def create(
        self,
        job: JobSpec,
        *,
        worker_run_id: str,
    ) -> DownloadWorkerPort:
        worker = GateWorker(job.job_id, worker_run_id, self.metrics)
        with self._condition:
            self.created.append(job.job_id)
            self.workers[job.job_id] = worker
            self._condition.notify_all()
        return worker

    def wait_created(self, count: int) -> bool:
        with self._condition:
            return self._condition.wait_for(lambda: len(self.created) >= count, timeout=2.0)


class FailFirstFactory:
    def __init__(self) -> None:
        self.created: list[str] = []

    def create(
        self,
        job: JobSpec,
        *,
        worker_run_id: str,
    ) -> DownloadWorkerPort:
        self.created.append(job.job_id)
        if len(self.created) == 1:
            raise DownloadWorkerError("cannot create worker")
        worker = GateWorker(job.job_id, worker_run_id, ActivityMetrics())
        worker.release()
        return worker


def make_job(index: int) -> JobSpec:
    return JobSpec(
        job_id=f"job-{index}",
        source_url=f"https://www.youtube.com/watch?v=video{index}",
        output_directory="Downloads",
        quality=QualityPreset.BEST,
        selected_subtitle=None,
    )


def run_id_factory() -> Iterable[str]:
    index = 0
    while True:
        index += 1
        yield f"run-{index}"


def test_default_concurrency_dispatches_two_jobs_and_preserves_fifo() -> None:
    factory = BlockingWorkerFactory()
    run_ids = iter(run_id_factory())
    queue = BoundedDownloadQueue(
        factory,
        worker_run_id_factory=lambda: next(run_ids),
    )

    queue.enqueue_many((make_job(1), make_job(2), make_job(3)))

    assert queue.concurrency == 2
    assert factory.wait_created(2)
    assert factory.created == ["job-1", "job-2"]
    assert factory.workers["job-1"].started.wait(2.0)
    assert factory.workers["job-2"].started.wait(2.0)
    assert queue.active_count == 2
    assert queue.pending_count == 1

    factory.workers["job-1"].release()
    assert factory.wait_created(3)
    assert factory.created == ["job-1", "job-2", "job-3"]
    assert factory.workers["job-3"].started.wait(2.0)
    assert factory.metrics.peak == 2

    factory.workers["job-2"].release()
    factory.workers["job-3"].release()
    queue.shutdown(wait=True)

    assert [snapshot.state for snapshot in queue.snapshots()] == [
        JobState.SUCCEEDED,
        JobState.SUCCEEDED,
        JobState.SUCCEEDED,
    ]


def test_queued_cancel_does_not_create_a_worker() -> None:
    factory = BlockingWorkerFactory()
    queue = BoundedDownloadQueue(
        factory,
        concurrency=1,
        worker_run_id_factory=iter(("run-1", "run-2")).__next__,
    )
    queue.enqueue_many((make_job(1), make_job(2)))

    assert factory.wait_created(1)
    assert factory.workers["job-1"].started.wait(2.0)

    cancelled = queue.cancel("job-2")
    assert cancelled.state is JobState.CANCELLED
    assert factory.created == ["job-1"]

    factory.workers["job-1"].release()
    queue.shutdown(wait=True)

    assert factory.created == ["job-1"]
    assert queue.snapshot("job-2").state is JobState.CANCELLED


def test_active_cancel_delegates_to_job_run_and_finishes_cancelled() -> None:
    factory = BlockingWorkerFactory()
    queue = BoundedDownloadQueue(
        factory,
        concurrency=1,
        worker_run_id_factory=lambda: "run-1",
    )
    queue.enqueue(make_job(1))

    assert factory.wait_created(1)
    worker = factory.workers["job-1"]
    assert worker.started.wait(2.0)

    snapshot = queue.cancel("job-1")
    assert snapshot.state in {JobState.CANCELLING, JobState.CANCELLED}

    queue.shutdown(wait=True)

    assert worker.cancel_requests == 1
    assert queue.snapshot("job-1").state is JobState.CANCELLED


def test_worker_creation_failure_interrupts_job_and_dispatches_next() -> None:
    factory = FailFirstFactory()
    queue = BoundedDownloadQueue(
        factory,
        concurrency=1,
        worker_run_id_factory=iter(("run-1", "run-2")).__next__,
    )

    queue.enqueue_many((make_job(1), make_job(2)))
    queue.shutdown(wait=True)

    assert factory.created == ["job-1", "job-2"]
    assert queue.snapshot("job-1").state is JobState.INTERRUPTED
    assert queue.snapshot("job-1").error_code == "worker_create_failed"
    assert queue.snapshot("job-2").state is JobState.SUCCEEDED


def test_enqueue_is_atomic_for_duplicate_ids() -> None:
    factory = BlockingWorkerFactory()
    queue = BoundedDownloadQueue(factory)

    with pytest.raises(ValueError, match="duplicate job_id"):
        queue.enqueue_many((make_job(1), make_job(1)))

    assert queue.snapshots() == ()
    queue.shutdown(wait=True)


def test_concurrency_is_bounded_to_supported_range() -> None:
    factory = BlockingWorkerFactory()

    with pytest.raises(ValueError, match="between 1 and 4"):
        BoundedDownloadQueue(factory, concurrency=0)
    with pytest.raises(ValueError, match="between 1 and 4"):
        BoundedDownloadQueue(factory, concurrency=5)
