import sqlite3
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
        display_title=f"Video {position}",
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
    assert loaded[0].job.display_title == "Video 0"


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


def test_sqlite_queue_migrates_v1_database_with_display_title_column(tmp_path: Path) -> None:
    database = tmp_path / "app.db"
    connection = sqlite3.connect(database)
    try:
        connection.executescript(
            """
            CREATE TABLE queue_jobs (
                job_id TEXT PRIMARY KEY,
                queue_position INTEGER NOT NULL UNIQUE,
                source_url TEXT NOT NULL,
                output_directory TEXT NOT NULL,
                quality TEXT NOT NULL,
                subtitle_language_code TEXT,
                subtitle_kind TEXT,
                subtitle_is_original INTEGER,
                subtitle_is_translated INTEGER,
                worker_run_id TEXT NOT NULL,
                state TEXT NOT NULL,
                progress_percent REAL,
                downloaded_bytes INTEGER,
                total_bytes INTEGER,
                speed_bytes_per_second REAL,
                eta_seconds REAL,
                output_paths_json TEXT NOT NULL,
                warning_message TEXT,
                error_code TEXT,
                error_message TEXT,
                last_sequence INTEGER,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE app_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            INSERT INTO app_meta(key, value) VALUES ('queue_schema_version', '1');
            """
        )
    finally:
        connection.close()

    SQLiteQueueStorage(database)

    connection = sqlite3.connect(database)
    try:
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(queue_jobs)").fetchall()
        }
        version = connection.execute(
            "SELECT value FROM app_meta WHERE key = 'queue_schema_version'"
        ).fetchone()
    finally:
        connection.close()

    assert "display_title" in columns
    assert version == ("2",)
