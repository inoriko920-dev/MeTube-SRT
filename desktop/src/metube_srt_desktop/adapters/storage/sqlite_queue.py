from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import cast

from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.application.dto.queue_storage import PersistedQueueEntry
from metube_srt_desktop.application.ports.queue_storage import (
    QueueStorageError,
    QueueStoragePort,
)
from metube_srt_desktop.domain.jobs import JobSpec, JobState, QualityPreset
from metube_srt_desktop.domain.subtitles import SubtitleKind, SubtitleTrack

_SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS queue_jobs (
    job_id TEXT PRIMARY KEY,
    queue_position INTEGER NOT NULL UNIQUE,
    source_url TEXT NOT NULL,
    display_title TEXT,
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

CREATE TABLE IF NOT EXISTS app_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class SQLiteQueueStorage(QueueStoragePort):
    """SQLite persistence for queue order, job history, outputs, and last state."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path).expanduser()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @property
    def database_path(self) -> Path:
        return self._database_path

    def load_entries(self) -> tuple[PersistedQueueEntry, ...]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT
                        job_id,
                        queue_position,
                        source_url,
                        display_title,
                        output_directory,
                        quality,
                        subtitle_language_code,
                        subtitle_kind,
                        subtitle_is_original,
                        subtitle_is_translated,
                        worker_run_id,
                        state,
                        progress_percent,
                        downloaded_bytes,
                        total_bytes,
                        speed_bytes_per_second,
                        eta_seconds,
                        output_paths_json,
                        warning_message,
                        error_code,
                        error_message,
                        last_sequence
                    FROM queue_jobs
                    ORDER BY queue_position ASC
                    """
                ).fetchall()
            return tuple(_row_to_entry(row) for row in rows)
        except (sqlite3.Error, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise QueueStorageError("durable queue could not be loaded") from exc

    def save_entries(self, entries: Iterable[PersistedQueueEntry]) -> None:
        records = tuple(entries)
        if not records:
            return

        try:
            with self._connect() as connection:
                connection.executemany(
                    """
                    INSERT INTO queue_jobs (
                        job_id,
                        queue_position,
                        source_url,
                        output_directory,
                        quality,
                        subtitle_language_code,
                        subtitle_kind,
                        subtitle_is_original,
                        subtitle_is_translated,
                        worker_run_id,
                        state,
                        progress_percent,
                        downloaded_bytes,
                        total_bytes,
                        speed_bytes_per_second,
                        eta_seconds,
                        output_paths_json,
                        warning_message,
                        error_code,
                        error_message,
                        last_sequence,
                        updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        CURRENT_TIMESTAMP
                    )
                    ON CONFLICT(job_id) DO UPDATE SET
                        queue_position=excluded.queue_position,
                        source_url=excluded.source_url,
                        display_title=excluded.display_title,
                        output_directory=excluded.output_directory,
                        quality=excluded.quality,
                        subtitle_language_code=excluded.subtitle_language_code,
                        subtitle_kind=excluded.subtitle_kind,
                        subtitle_is_original=excluded.subtitle_is_original,
                        subtitle_is_translated=excluded.subtitle_is_translated,
                        worker_run_id=excluded.worker_run_id,
                        state=excluded.state,
                        progress_percent=excluded.progress_percent,
                        downloaded_bytes=excluded.downloaded_bytes,
                        total_bytes=excluded.total_bytes,
                        speed_bytes_per_second=excluded.speed_bytes_per_second,
                        eta_seconds=excluded.eta_seconds,
                        output_paths_json=excluded.output_paths_json,
                        warning_message=excluded.warning_message,
                        error_code=excluded.error_code,
                        error_message=excluded.error_message,
                        last_sequence=excluded.last_sequence,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    [_entry_to_row(entry) for entry in records],
                )
        except sqlite3.Error as exc:
            raise QueueStorageError("durable queue could not be saved") from exc

    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.executescript(_SCHEMA)
                columns = {
                    str(row["name"])
                    for row in connection.execute("PRAGMA table_info(queue_jobs)").fetchall()
                }
                if "display_title" not in columns:
                    connection.execute("ALTER TABLE queue_jobs ADD COLUMN display_title TEXT")
                connection.execute(
                    """
                    INSERT INTO app_meta(key, value)
                    VALUES ('queue_schema_version', ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                    """,
                    (str(_SCHEMA_VERSION),),
                )
        except sqlite3.Error as exc:
            raise QueueStorageError("durable queue could not be initialized") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection


def _entry_to_row(entry: PersistedQueueEntry) -> tuple[object, ...]:
    subtitle = entry.job.selected_subtitle
    return (
        entry.job.job_id,
        entry.position,
        entry.job.source_url,
        entry.job.display_title,
        entry.job.output_directory,
        entry.job.quality.value,
        None if subtitle is None else subtitle.language_code,
        None if subtitle is None else subtitle.kind.value,
        None if subtitle is None else int(subtitle.is_original),
        None if subtitle is None else int(subtitle.is_translated),
        entry.snapshot.worker_run_id,
        entry.snapshot.state.value,
        entry.snapshot.progress_percent,
        entry.snapshot.downloaded_bytes,
        entry.snapshot.total_bytes,
        entry.snapshot.speed_bytes_per_second,
        entry.snapshot.eta_seconds,
        json.dumps(list(entry.snapshot.output_paths), ensure_ascii=False, separators=(",", ":")),
        entry.snapshot.warning_message,
        entry.snapshot.error_code,
        entry.snapshot.error_message,
        entry.snapshot.last_sequence,
    )


def _row_to_entry(row: sqlite3.Row) -> PersistedQueueEntry:
    mapping = cast(Mapping[str, object], row)
    subtitle = _row_to_subtitle(mapping)
    job = JobSpec(
        job_id=_require_str(mapping, "job_id"),
        source_url=_require_str(mapping, "source_url"),
        output_directory=_require_str(mapping, "output_directory"),
        quality=QualityPreset(_require_str(mapping, "quality")),
        selected_subtitle=subtitle,
        display_title=_optional_str(mapping, "display_title"),
    )
    output_paths = _decode_output_paths(_require_str(mapping, "output_paths_json"))
    snapshot = JobRuntimeSnapshot(
        job_id=job.job_id,
        worker_run_id=_require_str(mapping, "worker_run_id"),
        state=JobState(_require_str(mapping, "state")),
        progress_percent=_optional_float(mapping, "progress_percent"),
        downloaded_bytes=_optional_int(mapping, "downloaded_bytes"),
        total_bytes=_optional_int(mapping, "total_bytes"),
        speed_bytes_per_second=_optional_float(mapping, "speed_bytes_per_second"),
        eta_seconds=_optional_float(mapping, "eta_seconds"),
        output_paths=output_paths,
        warning_message=_optional_str(mapping, "warning_message"),
        error_code=_optional_str(mapping, "error_code"),
        error_message=_optional_str(mapping, "error_message"),
        last_sequence=_optional_int(mapping, "last_sequence"),
    )
    return PersistedQueueEntry(
        position=_require_int(mapping, "queue_position"),
        job=job,
        snapshot=snapshot,
    )


def _row_to_subtitle(row: Mapping[str, object]) -> SubtitleTrack | None:
    language = _optional_str(row, "subtitle_language_code")
    kind = _optional_str(row, "subtitle_kind")
    is_original = _optional_int(row, "subtitle_is_original")
    is_translated = _optional_int(row, "subtitle_is_translated")
    if language is None and kind is None:
        return None
    if language is None or kind is None or is_original is None or is_translated is None:
        raise ValueError("persisted subtitle metadata is incomplete")
    return SubtitleTrack(
        language_code=language,
        kind=SubtitleKind(kind),
        is_original=bool(is_original),
        is_translated=bool(is_translated),
    )


def _decode_output_paths(raw: str) -> tuple[str, ...]:
    value = cast(object, json.loads(raw))
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError("output_paths_json must contain an array")
    paths: list[str] = []
    for item in cast(Sequence[object], value):
        if not isinstance(item, str):
            raise ValueError("output_paths_json must contain only strings")
        paths.append(item)
    return tuple(paths)


def _require_str(row: Mapping[str, object], key: str) -> str:
    value = row[key]
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _optional_str(row: Mapping[str, object], key: str) -> str | None:
    value = row[key]
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string or null")
    return value


def _require_int(row: Mapping[str, object], key: str) -> int:
    value = row[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return value


def _optional_int(row: Mapping[str, object], key: str) -> int | None:
    value = row[key]
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer or null")
    return value


def _optional_float(row: Mapping[str, object], key: str) -> float | None:
    value = row[key]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric or null")
    return float(value)
