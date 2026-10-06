from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import replace

from metube_srt_desktop.application.dto.queue_storage import PersistedQueueEntry
from metube_srt_desktop.domain.jobs import JobState, transition_job_state

_ACTIVE_AT_RESTART = {
    JobState.RESOLVING,
    JobState.RUNNING,
    JobState.POSTPROCESSING,
    JobState.CANCELLING,
}


def recover_persisted_entries(
    entries: Iterable[PersistedQueueEntry],
    *,
    worker_run_id_factory: Callable[[], str],
) -> tuple[PersistedQueueEntry, ...]:
    """Apply conservative restart rules to durable queue/history records."""

    ordered = tuple(sorted(entries, key=lambda entry: entry.position))
    _validate_unique_records(ordered)

    recovered: list[PersistedQueueEntry] = []
    for entry in ordered:
        snapshot = entry.snapshot
        if snapshot.state is JobState.QUEUED:
            worker_run_id = worker_run_id_factory()
            if not worker_run_id.strip():
                raise ValueError("worker_run_id_factory returned an empty value")
            snapshot = replace(
                snapshot,
                worker_run_id=worker_run_id,
                progress_percent=None,
                downloaded_bytes=None,
                total_bytes=None,
                speed_bytes_per_second=None,
                eta_seconds=None,
                output_paths=(),
                warning_message=None,
                error_code=None,
                error_message=None,
                last_sequence=None,
            )
        elif snapshot.state in _ACTIVE_AT_RESTART:
            snapshot = replace(
                snapshot,
                state=transition_job_state(snapshot.state, JobState.INTERRUPTED),
                error_code="app_restart_interrupted",
                error_message="Application restarted while this job was active",
            )

        recovered.append(
            PersistedQueueEntry(
                position=entry.position,
                job=entry.job,
                snapshot=snapshot,
            )
        )

    return tuple(recovered)


def _validate_unique_records(entries: tuple[PersistedQueueEntry, ...]) -> None:
    job_ids: set[str] = set()
    positions: set[int] = set()
    for entry in entries:
        if entry.job.job_id in job_ids:
            raise ValueError(f"duplicate persisted job_id: {entry.job.job_id}")
        if entry.position in positions:
            raise ValueError(f"duplicate persisted queue position: {entry.position}")
        job_ids.add(entry.job.job_id)
        positions.add(entry.position)
