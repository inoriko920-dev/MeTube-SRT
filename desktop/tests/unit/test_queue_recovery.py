import pytest

from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.application.dto.queue_storage import PersistedQueueEntry
from metube_srt_desktop.application.queue_recovery import recover_persisted_entries
from metube_srt_desktop.domain.jobs import JobSpec, JobState, QualityPreset


def make_entry(
    position: int,
    *,
    state: JobState,
    worker_run_id: str,
) -> PersistedQueueEntry:
    job = JobSpec(
        job_id=f"job-{position}",
        source_url=f"https://www.youtube.com/watch?v=video{position}",
        output_directory="Downloads",
        quality=QualityPreset.BEST,
        selected_subtitle=None,
    )
    snapshot = JobRuntimeSnapshot(
        job_id=job.job_id,
        worker_run_id=worker_run_id,
        state=state,
        progress_percent=50.0,
        downloaded_bytes=500,
        total_bytes=1000,
        output_paths=("Downloads/old.mp4",),
        warning_message="old warning",
        error_code="old_error",
        error_message="old error",
        last_sequence=4,
    )
    return PersistedQueueEntry(position=position, job=job, snapshot=snapshot)


def test_restart_recovery_requeues_only_previously_queued_jobs() -> None:
    queued = make_entry(0, state=JobState.QUEUED, worker_run_id="old-queued-run")
    running = make_entry(1, state=JobState.RUNNING, worker_run_id="old-running-run")
    succeeded = make_entry(2, state=JobState.SUCCEEDED, worker_run_id="old-success-run")

    recovered = recover_persisted_entries(
        (succeeded, running, queued),
        worker_run_id_factory=lambda: "new-queued-run",
    )

    assert [entry.position for entry in recovered] == [0, 1, 2]

    recovered_queued = recovered[0].snapshot
    assert recovered_queued.state is JobState.QUEUED
    assert recovered_queued.worker_run_id == "new-queued-run"
    assert recovered_queued.progress_percent is None
    assert recovered_queued.output_paths == ()
    assert recovered_queued.last_sequence is None

    recovered_running = recovered[1].snapshot
    assert recovered_running.state is JobState.INTERRUPTED
    assert recovered_running.worker_run_id == "old-running-run"
    assert recovered_running.error_code == "app_restart_interrupted"

    assert recovered[2] == succeeded


def test_restart_recovery_rejects_duplicate_positions() -> None:
    first = make_entry(0, state=JobState.QUEUED, worker_run_id="run-1")
    second_job = JobSpec(
        job_id="job-other",
        source_url="https://www.youtube.com/watch?v=other",
        output_directory="Downloads",
        quality=QualityPreset.BEST,
        selected_subtitle=None,
    )
    second = PersistedQueueEntry(
        position=0,
        job=second_job,
        snapshot=JobRuntimeSnapshot(
            job_id="job-other",
            worker_run_id="run-2",
            state=JobState.QUEUED,
        ),
    )

    with pytest.raises(ValueError, match="duplicate persisted queue position"):
        recover_persisted_entries(
            (first, second),
            worker_run_id_factory=lambda: "new-run",
        )
