from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from queue import Empty, SimpleQueue
from threading import RLock
from uuid import uuid4

from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.application.job_lifecycle import DownloadJobRun
from metube_srt_desktop.application.ports.download_worker import (
    DownloadWorkerError,
    DownloadWorkerFactoryPort,
)
from metube_srt_desktop.domain.jobs import (
    JobSpec,
    JobState,
    is_terminal_job_state,
    transition_job_state,
)

DEFAULT_DOWNLOAD_CONCURRENCY = 2
MAX_DOWNLOAD_CONCURRENCY = 4


@dataclass(slots=True)
class _QueueEntry:
    job: JobSpec
    worker_run_id: str
    snapshot: JobRuntimeSnapshot
    run: DownloadJobRun | None = None


def _new_worker_run_id() -> str:
    return uuid4().hex


class BoundedDownloadQueue:
    """Application-owned FIFO scheduler with bounded worker concurrency."""

    def __init__(
        self,
        worker_factory: DownloadWorkerFactoryPort,
        *,
        concurrency: int = DEFAULT_DOWNLOAD_CONCURRENCY,
        worker_run_id_factory: Callable[[], str] = _new_worker_run_id,
    ) -> None:
        if not 1 <= concurrency <= MAX_DOWNLOAD_CONCURRENCY:
            raise ValueError(f"concurrency must be between 1 and {MAX_DOWNLOAD_CONCURRENCY}")

        self._worker_factory = worker_factory
        self._concurrency = concurrency
        self._worker_run_id_factory = worker_run_id_factory
        self._lock = RLock()
        self._pending: deque[str] = deque()
        self._entries: dict[str, _QueueEntry] = {}
        self._active: set[str] = set()
        self._updates: SimpleQueue[JobRuntimeSnapshot] = SimpleQueue()
        self._closed = False
        self._executor = ThreadPoolExecutor(
            max_workers=concurrency,
            thread_name_prefix="metube-download",
        )

    @property
    def concurrency(self) -> int:
        return self._concurrency

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    @property
    def pending_count(self) -> int:
        with self._lock:
            return sum(
                1
                for job_id in self._pending
                if self._entries[job_id].snapshot.state is JobState.QUEUED
            )

    def enqueue(self, job: JobSpec) -> JobRuntimeSnapshot:
        return self.enqueue_many((job,))[0]

    def enqueue_many(self, jobs: Iterable[JobSpec]) -> tuple[JobRuntimeSnapshot, ...]:
        batch = tuple(jobs)
        if not batch:
            return ()

        batch_ids = [job.job_id for job in batch]
        if len(set(batch_ids)) != len(batch_ids):
            raise ValueError("batch contains duplicate job_id values")

        with self._lock:
            self._ensure_open()
            duplicates = [job_id for job_id in batch_ids if job_id in self._entries]
            if duplicates:
                raise ValueError(f"job_id already exists: {duplicates[0]}")

            snapshots: list[JobRuntimeSnapshot] = []
            for job in batch:
                worker_run_id = self._worker_run_id_factory()
                if not worker_run_id.strip():
                    raise ValueError("worker_run_id_factory returned an empty value")
                snapshot = JobRuntimeSnapshot(
                    job_id=job.job_id,
                    worker_run_id=worker_run_id,
                    state=JobState.QUEUED,
                )
                self._entries[job.job_id] = _QueueEntry(
                    job=job,
                    worker_run_id=worker_run_id,
                    snapshot=snapshot,
                )
                self._pending.append(job.job_id)
                self._publish_locked(snapshot)
                snapshots.append(snapshot)

            self._dispatch_available_locked()
            return tuple(snapshots)

    def cancel(self, job_id: str) -> JobRuntimeSnapshot:
        with self._lock:
            entry = self._require_entry(job_id)
            if is_terminal_job_state(entry.snapshot.state):
                return entry.snapshot

            run = entry.run
            if run is None:
                entry.snapshot = replace(
                    entry.snapshot,
                    state=transition_job_state(entry.snapshot.state, JobState.CANCELLED),
                )
                self._publish_locked(entry.snapshot)
                return entry.snapshot

        snapshot = run.cancel()
        with self._lock:
            entry = self._require_entry(job_id)
            self._accept_snapshot_locked(entry, snapshot)
            return entry.snapshot

    def snapshot(self, job_id: str) -> JobRuntimeSnapshot:
        with self._lock:
            return self._require_entry(job_id).snapshot

    def snapshots(self) -> tuple[JobRuntimeSnapshot, ...]:
        with self._lock:
            return tuple(entry.snapshot for entry in self._entries.values())

    def drain_updates(self) -> tuple[JobRuntimeSnapshot, ...]:
        updates: list[JobRuntimeSnapshot] = []
        while True:
            try:
                updates.append(self._updates.get_nowait())
            except Empty:
                return tuple(updates)

    def shutdown(self, *, wait: bool = True, cancel_active: bool = False) -> None:
        active_runs: tuple[DownloadJobRun, ...] = ()
        with self._lock:
            if not self._closed:
                self._closed = True
                if cancel_active:
                    active_runs = tuple(
                        entry.run
                        for job_id in tuple(self._active)
                        if (entry := self._entries[job_id]).run is not None
                    )

        for run in active_runs:
            run.cancel()

        self._executor.shutdown(wait=wait, cancel_futures=False)

    def _dispatch_available_locked(self) -> None:
        if self._closed:
            return

        while len(self._active) < self._concurrency and self._pending:
            job_id = self._pending.popleft()
            entry = self._entries[job_id]
            if entry.snapshot.state is not JobState.QUEUED:
                continue

            try:
                worker = self._worker_factory.create(
                    entry.job,
                    worker_run_id=entry.worker_run_id,
                )
            except DownloadWorkerError:
                entry.snapshot = replace(
                    entry.snapshot,
                    state=transition_job_state(entry.snapshot.state, JobState.INTERRUPTED),
                    error_code="worker_create_failed",
                    error_message="Download worker could not be created",
                )
                self._publish_locked(entry.snapshot)
                continue

            run = DownloadJobRun(
                entry.job,
                worker_run_id=entry.worker_run_id,
                worker=worker,
            )
            entry.run = run
            self._active.add(job_id)
            self._executor.submit(self._drive_job, job_id, run)

    def _drive_job(self, job_id: str, run: DownloadJobRun) -> None:
        try:
            for snapshot in run.updates():
                with self._lock:
                    entry = self._entries[job_id]
                    if entry.run is run:
                        self._accept_snapshot_locked(entry, snapshot)
        finally:
            with self._lock:
                entry = self._entries[job_id]
                if entry.run is run and not is_terminal_job_state(entry.snapshot.state):
                    entry.snapshot = replace(
                        entry.snapshot,
                        state=transition_job_state(
                            entry.snapshot.state,
                            JobState.INTERRUPTED,
                        ),
                        error_code="scheduler_run_interrupted",
                        error_message="Download job execution was interrupted",
                    )
                    self._publish_locked(entry.snapshot)

                self._active.discard(job_id)
                self._dispatch_available_locked()

    def _accept_snapshot_locked(
        self,
        entry: _QueueEntry,
        candidate: JobRuntimeSnapshot,
    ) -> None:
        current = entry.snapshot
        if candidate.worker_run_id != entry.worker_run_id:
            return
        if is_terminal_job_state(current.state) and not is_terminal_job_state(candidate.state):
            return

        current_sequence = current.last_sequence
        candidate_sequence = candidate.last_sequence
        if (
            current_sequence is not None
            and candidate_sequence is not None
            and candidate_sequence < current_sequence
        ):
            return

        if candidate == current:
            return
        entry.snapshot = candidate
        self._publish_locked(candidate)

    def _publish_locked(self, snapshot: JobRuntimeSnapshot) -> None:
        self._updates.put(snapshot)

    def _require_entry(self, job_id: str) -> _QueueEntry:
        try:
            return self._entries[job_id]
        except KeyError as exc:
            raise KeyError(f"unknown job_id: {job_id}") from exc

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("download queue is shut down")
