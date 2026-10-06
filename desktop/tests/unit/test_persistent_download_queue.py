from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from metube_srt_desktop.adapters.storage import SQLiteQueueStorage
from metube_srt_desktop.application.download_queue import BoundedDownloadQueue
from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.application.dto.queue_storage import PersistedQueueEntry
from metube_srt_desktop.application.dto.worker_protocol import (
    WORKER_PROTOCOL_VERSION,
    WorkerEnvelope,
    WorkerEventType,
)
from metube_srt_desktop.application.ports.download_worker import DownloadWorkerPort
from metube_srt_desktop.domain.jobs import JobSpec, JobState, QualityPreset


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


class CapturingFactory:
    def __init__(self) -> None:
        self.created: list[tuple[str, str]] = []

    def create(
        self,
        job: JobSpec,
        *,
        worker_run_id: str,
    ) -> DownloadWorkerPort:
        self.created.append((job.job_id, worker_run_id))
        return ImmediateWorker(job.job_id, worker_run_id)


def make_job(index: int) -> JobSpec:
    return JobSpec(
        job_id=f"job-{index}",
        source_url=f"https://www.youtube.com/watch?v=video{index}",
        output_directory="Downloads",
        quality=QualityPreset.BEST,
        selected_subtitle=None,
    )


def record(
    position: int,
    *,
    state: JobState,
    worker_run_id: str,
) -> PersistedQueueEntry:
    job = make_job(position)
    return PersistedQueueEntry(
        position=position,
        job=job,
        snapshot=JobRuntimeSnapshot(
            job_id=job.job_id,
            worker_run_id=worker_run_id,
            state=state,
            progress_percent=40.0 if state is JobState.RUNNING else None,
            last_sequence=3 if state is JobState.RUNNING else None,
        ),
    )


def test_queue_persists_terminal_state_after_execution(tmp_path: Path) -> None:
    storage = SQLiteQueueStorage(tmp_path / "app.db")
    factory = CapturingFactory()
    queue = BoundedDownloadQueue(
        factory,
        concurrency=1,
        worker_run_id_factory=lambda: "run-1",
        storage=storage,
    )

    queue.enqueue(make_job(1))
    queue.shutdown(wait=True)

    loaded = storage.load_entries()
    assert len(loaded) == 1
    assert loaded[0].position == 0
    assert loaded[0].snapshot.state is JobState.SUCCEEDED
    assert loaded[0].snapshot.last_sequence == 1


def test_restore_interrupts_old_active_job_and_dispatches_only_old_queued_job(
    tmp_path: Path,
) -> None:
    storage = SQLiteQueueStorage(tmp_path / "app.db")
    storage.save_entries(
        (
            record(0, state=JobState.RUNNING, worker_run_id="old-active"),
            record(1, state=JobState.QUEUED, worker_run_id="old-queued"),
            record(2, state=JobState.SUCCEEDED, worker_run_id="old-success"),
        )
    )
    factory = CapturingFactory()

    queue = BoundedDownloadQueue.restore(
        factory,
        storage,
        concurrency=1,
        worker_run_id_factory=lambda: "new-queued-run",
    )
    queue.shutdown(wait=True)

    assert factory.created == [("job-1", "new-queued-run")]
    snapshots = queue.snapshots()
    assert [snapshot.state for snapshot in snapshots] == [
        JobState.INTERRUPTED,
        JobState.SUCCEEDED,
        JobState.SUCCEEDED,
    ]

    persisted = storage.load_entries()
    assert persisted[0].snapshot.error_code == "app_restart_interrupted"
    assert persisted[0].snapshot.worker_run_id == "old-active"
    assert persisted[1].snapshot.worker_run_id == "new-queued-run"
    assert persisted[1].snapshot.state is JobState.SUCCEEDED



def test_restore_rejects_duplicate_queued_targets_before_dispatch(tmp_path: Path) -> None:
    storage = SQLiteQueueStorage(tmp_path / "app.db")
    first = make_job(10)
    second = JobSpec(
        job_id="job-11",
        source_url=first.source_url,
        output_directory=first.output_directory,
        quality=QualityPreset.P720,
        selected_subtitle=None,
    )
    storage.save_entries(
        (
            PersistedQueueEntry(
                position=0,
                job=first,
                snapshot=JobRuntimeSnapshot(
                    job_id=first.job_id,
                    worker_run_id="old-1",
                    state=JobState.QUEUED,
                ),
            ),
            PersistedQueueEntry(
                position=1,
                job=second,
                snapshot=JobRuntimeSnapshot(
                    job_id=second.job_id,
                    worker_run_id="old-2",
                    state=JobState.QUEUED,
                ),
            ),
        )
    )
    factory = CapturingFactory()

    import pytest

    with pytest.raises(ValueError, match="duplicate active download target"):
        BoundedDownloadQueue.restore(factory, storage, concurrency=1)

    assert factory.created == []
