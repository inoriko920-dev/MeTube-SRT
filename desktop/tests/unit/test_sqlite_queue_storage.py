from pathlib import Path

from metube_srt_desktop.adapters.storage import SQLiteQueueStorage
from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.application.dto.queue_storage import PersistedQueueEntry
from metube_srt_desktop.domain.jobs import JobSpec, JobState, QualityPreset
from metube_srt_desktop.domain.subtitles import SubtitleKind, SubtitleTrack


def make_entry(position: int, *, state: JobState) -> PersistedQueueEntry:
    job_id = f"job-{position}"
    subtitle = SubtitleTrack(
        language_code="id",
        kind=SubtitleKind.MANUAL,
        is_original=True,
    )
    job = JobSpec(
        job_id=job_id,
        source_url=f"https://www.youtube.com/watch?v=video{position}",
        output_directory="Downloads",
        quality=QualityPreset.P1080,
        selected_subtitle=subtitle,
    )
    snapshot = JobRuntimeSnapshot(
        job_id=job_id,
        worker_run_id=f"run-{position}",
        state=state,
        progress_percent=75.0,
        downloaded_bytes=750,
        total_bytes=1000,
        speed_bytes_per_second=125.5,
        eta_seconds=2.0,
        output_paths=(f"Downloads/video-{position}.mp4",),
        warning_message="warning",
        error_code=None,
        error_message=None,
        last_sequence=7,
    )
    return PersistedQueueEntry(position=position, job=job, snapshot=snapshot)


def test_sqlite_queue_round_trip_preserves_order_and_metadata(tmp_path: Path) -> None:
    storage = SQLiteQueueStorage(tmp_path / "app.db")
    second = make_entry(1, state=JobState.SUCCEEDED)
    first = make_entry(0, state=JobState.RUNNING)

    storage.save_entries((second, first))

    loaded = storage.load_entries()

    assert loaded == (first, second)
    assert loaded[0].job.selected_subtitle is not None
    assert loaded[0].job.selected_subtitle.kind is SubtitleKind.MANUAL
    assert loaded[1].snapshot.output_paths == ("Downloads/video-1.mp4",)


def test_sqlite_queue_upsert_updates_last_health_state(tmp_path: Path) -> None:
    storage = SQLiteQueueStorage(tmp_path / "app.db")
    original = make_entry(0, state=JobState.RUNNING)
    updated = PersistedQueueEntry(
        position=0,
        job=original.job,
        snapshot=JobRuntimeSnapshot(
            job_id=original.job.job_id,
            worker_run_id=original.snapshot.worker_run_id,
            state=JobState.INTERRUPTED,
            progress_percent=80.0,
            downloaded_bytes=800,
            total_bytes=1000,
            output_paths=("Downloads/partial.mp4",),
            error_code="app_restart_interrupted",
            error_message="Application restarted while this job was active",
            last_sequence=8,
        ),
    )

    storage.save_entries((original,))
    storage.save_entries((updated,))

    assert storage.load_entries() == (updated,)
