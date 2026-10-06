from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from queue import Empty, SimpleQueue
from threading import RLock
from uuid import uuid4

from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.application.dto.queue_storage import PersistedQueueEntry
from metube_srt_desktop.application.job_lifecycle import DownloadJobRun
from metube_srt_desktop.application.ports.download_worker import (
    DownloadWorkerError,
    DownloadWorkerFactoryPort,
)
from metube_srt_desktop.application.ports.queue_storage import (
    QueueStorageError,
    QueueStoragePort,
)
from metube_srt_desktop.application.queue_recovery import recover_persisted_entries
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
    position: int
    job: JobSpec
    worker_run_id: str
    snapshot: JobRuntimeSnapshot
    run: DownloadJobRun | None = None


def _new_worker_run_id() -> str:
    return uuid4().hex


class BoundedDownloadQueue:
    """Application-owned FIFO scheduler with optional durable persistence."""

    def __init__(
        self,
        worker_factory: DownloadWorkerFactoryPort,
        *,
        concurrency: int = DEFAULT_DOWNLOAD_CONCURRENCY,
        worker_run_id_factory: Callable[[], str] = _new_worker_run_id,
        storage: QueueStoragePort | None = None,
    ) -> None:
        if not 1 <= concurrency <= MAX_DOWNLOAD_CONCURRENCY:
            raise ValueError(f"concurrency must be between 1 and {MAX_DOWNLOAD_CONCURRENCY}")

        self._worker_factory = worker_factory
        self._concurrency = concurrency
        self._worker_run_id_factory = worker_run_id_factory
        self._storage = storage
        self._lock = RLock()
        self._pending: deque[str] = deque()
        self._entries: dict[str, _QueueEntry] = {}
        self._active: set[str] = set()
        self._updates: SimpleQueue[JobRuntimeSnapshot] = SimpleQueue()
        self._next_position = 0
        self._closed = False
        self._persistence_failed = False
        self._executor = ThreadPoolExecutor(
            max_workers=concurrency,
            thread_name_prefix="metube-download",
        )

    @classmethod
    def restore(
        cls,
        worker_factory: DownloadWorkerFactoryPort,
        storage: QueueStoragePort,
        *,
        concurrency: int = DEFAULT_DOWNLOAD_CONCURRENCY,
        worker_run_id_factory: Callable[[], str] = _new_worker_run_id,
    ) -> BoundedDownloadQueue:
        """Reconstruct queue/history and apply restart-safe recovery rules."""

        queue = cls(
            worker_factory,
            concurrency=concurrency,
            worker_run_id_factory=worker_run_id_factory,
            storage=storage,
        )
        try:
            loaded = storage.load_entries()
            recovered = recover_persisted_entries(
                loaded,
                worker_run_id_factory=worker_run_id_factory,
            )
            storage.save_entries(recovered)

            with queue._lock:
                for record in recovered:
                    entry = _QueueEntry(
                        position=record.position,
                        job=record.job,
                        worker_run_id=record.snapshot.worker_run_id,
                        snapshot=record.snapshot,
                    )
                    queue._entries[entry.job.job_id] = entry
                    queue._next_position = max(queue._next_position, entry.position + 1)
                    if entry.snapshot.state is JobState.QUEUED:
                        queue._pending.append(entry.job.job_id)
                    queue._updates.put(entry.snapshot)

                queue._dispatch_available_locked()
        except BaseException:
            queue.shutdown(wait=False, cancel_active=True)
            raise

        return queue

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

    @property
    def persistence_healthy(self) -> bool:
        with self._lock:
            return not self._persistence_failed

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
            self._ensure_persistence_healthy()
            duplicates = [job_id for job_id in batch_ids if job_id in self._entries]
            if duplicates:
                raise ValueError(f"job_id already exists: {duplicates[0]}")

            staged: list[_QueueEntry] = []
            next_position = self._next_position
            for job in batch:
                worker_run_id = self._worker_run_id_factory()
                if not worker_run_id.strip():
                    raise ValueError("worker_run_id_factory returned an empty value")
                snapshot = JobRuntimeSnapshot(
                    job_id=job.job_id,
                    worker_run_id=worker_run_id,
                    state=JobState.QUEUED,
                )
                staged.append(
                    _QueueEntry(
                        position=next_position,
                        job=job,
                        worker_run_id=worker_run_id,
                        snapshot=snapshot,
                    )
                )
                next_position += 1

            self._persist_entries_locked(staged)

            for entry in staged:
                self._entries[entry.job.job_id] = entry
                self._pending.append(entry.job.job_id)
                self._updates.put(entry.snapshot)
            self._next_position = next_position

            self._dispatch_available_locked()
            return tuple(entry.snapshot for entry in staged)

    def cancel(self, job_id: str) -> JobRuntimeSnapshot:
        with self._lock:
            entry = self._require_entry(job_id)
            if is_terminal_job_state(entry.snapshot.state):
                return entry.snapshot

            run = entry.run
            if run is None:
                candidate = replace(
                    entry.snapshot,
                    state=transition_job_state(entry.snapshot.state, JobState.CANCELLED),
                )
                self._commit_snapshot_locked(entry, candidate)
                return entry.snapshot

        snapshot = run.cancel()
        with self._lock:
            entry = self._require_entry(job_id)
            try:
                self._accept_snapshot_locked(entry, snapshot)
            except QueueStorageError:
                self._mark_persistence_failure_locked(entry)
                raise
            return entry.snapshot

    def snapshot(self, job_id: str) -> JobRuntimeSnapshot:
        with self._lock:
            return self._require_entry(job_id).snapshot

    def snapshots(self) -> tuple[JobRuntimeSnapshot, ...]:
        with self._lock:
            return tuple(entry.snapshot for entry in self._entries.values())

    def job_specs(self) -> tuple[JobSpec, ...]:
        with self._lock:
            return tuple(entry.job for entry in self._entries.values())

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

        try:
            for run in active_runs:
                try:
                    run.cancel()
                except DownloadWorkerError:
                    continue
        finally:
            self._executor.shutdown(wait=wait, cancel_futures=False)

    def _dispatch_available_locked(self) -> None:
        if self._closed or self._persistence_failed:
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
                candidate = replace(
                    entry.snapshot,
                    state=transition_job_state(entry.snapshot.state, JobState.INTERRUPTED),
                    error_code="worker_create_failed",
                    error_message="Download worker could not be created",
                )
                try:
                    self._commit_snapshot_locked(entry, candidate)
                except QueueStorageError:
                    self._mark_persistence_failure_locked(entry)
                    return
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
        storage_failed = False
        try:
            for snapshot in run.updates():
                with self._lock:
                    entry = self._entries[job_id]
                    if entry.run is not run:
                        continue
                    try:
                        self._accept_snapshot_locked(entry, snapshot)
                    except QueueStorageError:
                        self._mark_persistence_failure_locked(entry)
                        storage_failed = True
                        break
        finally:
            if storage_failed:
                run.cancel()

            with self._lock:
                entry = self._entries[job_id]
                if (
                    not storage_failed
                    and entry.run is run
                    and not is_terminal_job_state(entry.snapshot.state)
                ):
                    candidate = replace(
                        entry.snapshot,
                        state=transition_job_state(
                            entry.snapshot.state,
                            JobState.INTERRUPTED,
                        ),
                        error_code="scheduler_run_interrupted",
                        error_message="Download job execution was interrupted",
                    )
                    try:
                        self._commit_snapshot_locked(entry, candidate)
                    except QueueStorageError:
                        self._mark_persistence_failure_locked(entry)

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
        self._commit_snapshot_locked(entry, candidate)

    def _commit_snapshot_locked(
        self,
        entry: _QueueEntry,
        candidate: JobRuntimeSnapshot,
    ) -> None:
        self._persist_records_locked(
            (
                PersistedQueueEntry(
                    position=entry.position,
                    job=entry.job,
                    snapshot=candidate,
                ),
            )
        )
        entry.snapshot = candidate
        self._updates.put(candidate)

    def _persist_entries_locked(self, entries: Iterable[_QueueEntry]) -> None:
        self._persist_records_locked(
            PersistedQueueEntry(
                position=entry.position,
                job=entry.job,
                snapshot=entry.snapshot,
            )
            for entry in entries
        )

    def _persist_records_locked(self, records: Iterable[PersistedQueueEntry]) -> None:
        if self._storage is None:
            return
        self._storage.save_entries(records)

    def _mark_persistence_failure_locked(self, entry: _QueueEntry) -> None:
        self._persistence_failed = True
        if not is_terminal_job_state(entry.snapshot.state):
            entry.snapshot = replace(
                entry.snapshot,
                state=transition_job_state(entry.snapshot.state, JobState.INTERRUPTED),
                error_code="storage_write_failed",
                error_message="Durable queue storage became unavailable",
            )
            self._updates.put(entry.snapshot)

    def _require_entry(self, job_id: str) -> _QueueEntry:
        try:
            return self._entries[job_id]
        except KeyError as exc:
            raise KeyError(f"unknown job_id: {job_id}") from exc

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("download queue is shut down")

    def _ensure_persistence_healthy(self) -> None:
        if self._persistence_failed:
            raise QueueStorageError("durable queue storage is unavailable")
