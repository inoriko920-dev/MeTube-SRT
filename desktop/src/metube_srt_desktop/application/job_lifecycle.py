from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
from threading import Lock

from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.application.dto.worker_protocol import WorkerEnvelope, WorkerEventType
from metube_srt_desktop.application.ports.download_worker import (
    DownloadWorkerError,
    DownloadWorkerPort,
)
from metube_srt_desktop.domain.jobs import (
    JobSpec,
    JobState,
    is_terminal_job_state,
    transition_job_state,
)


class DownloadJobRun:
    """Application-owned lifecycle for one immutable download job attempt."""

    def __init__(
        self,
        job: JobSpec,
        *,
        worker_run_id: str,
        worker: DownloadWorkerPort,
    ) -> None:
        if not worker_run_id.strip():
            raise ValueError("worker_run_id must be non-empty")

        self._job = job
        self._worker = worker
        self._lock = Lock()
        self._updates_claimed = False
        self._snapshot = JobRuntimeSnapshot(
            job_id=job.job_id,
            worker_run_id=worker_run_id,
            state=JobState.QUEUED,
        )

    @property
    def snapshot(self) -> JobRuntimeSnapshot:
        with self._lock:
            return self._snapshot

    def cancel(self) -> JobRuntimeSnapshot:
        with self._lock:
            if is_terminal_job_state(self._snapshot.state):
                return self._snapshot
            self._snapshot = replace(
                self._snapshot,
                state=transition_job_state(self._snapshot.state, JobState.CANCELLING),
            )

        try:
            self._worker.request_cancel()
        except DownloadWorkerError as exc:
            return self._mark_interrupted(
                "worker_cancel_failed",
                _worker_error_message(exc, "Download worker cancellation failed"),
            )

        return self.snapshot

    def updates(self) -> Iterable[JobRuntimeSnapshot]:
        with self._lock:
            if self._updates_claimed:
                raise RuntimeError("job updates can only be consumed once")
            self._updates_claimed = True

        terminal_event: WorkerEnvelope | None = None
        try:
            for event in self._worker.events():
                if not self._is_current_event(event):
                    continue
                if event.event_type in {
                    WorkerEventType.SUCCEEDED,
                    WorkerEventType.FAILED,
                    WorkerEventType.CANCELLED,
                }:
                    terminal_event = event
                    continue
                yield self._apply_event(event)
        except DownloadWorkerError as exc:
            if self.snapshot.state is JobState.CANCELLING:
                yield self._mark_cancelled_after_worker_stop()
            else:
                yield self._mark_interrupted(
                    "worker_process_failed",
                    _worker_error_message(exc, "Download worker process failed"),
                )
            return

        if terminal_event is not None:
            yield self._apply_event(terminal_event)
            return

        yield self._mark_interrupted(
            "worker_stream_ended",
            "Download worker stream ended before a terminal event",
        )

    def _is_current_event(self, event: WorkerEnvelope) -> bool:
        snapshot = self.snapshot
        return event.job_id == snapshot.job_id and event.worker_run_id == snapshot.worker_run_id

    def _apply_event(self, event: WorkerEnvelope) -> JobRuntimeSnapshot:
        with self._lock:
            current = self._snapshot
            if is_terminal_job_state(current.state):
                return current

            next_state = _state_for_event(current.state, event)
            changes: dict[str, object] = {
                "state": next_state,
                "last_sequence": event.sequence,
            }

            if event.event_type is WorkerEventType.PROGRESS:
                changes.update(_progress_changes(event.payload))
            elif event.event_type is WorkerEventType.WARNING:
                changes["warning_message"] = _optional_text(event.payload, "message")
            elif event.event_type is WorkerEventType.OUTPUT_READY:
                output_path = _optional_text(event.payload, "path")
                if output_path is not None and output_path not in current.output_paths:
                    changes["output_paths"] = (*current.output_paths, output_path)
            elif event.event_type is WorkerEventType.FAILED:
                changes["error_code"] = _optional_text(event.payload, "error_code")
                changes["error_message"] = (
                    _optional_text(event.payload, "message") or "Download worker reported failure"
                )

            self._snapshot = replace(current, **changes)
            return self._snapshot

    def _mark_cancelled_after_worker_stop(self) -> JobRuntimeSnapshot:
        with self._lock:
            current = self._snapshot
            if is_terminal_job_state(current.state):
                return current
            self._snapshot = replace(
                current,
                state=transition_job_state(current.state, JobState.CANCELLED),
                warning_message="Worker dihentikan paksa setelah permintaan pembatalan",
            )
            return self._snapshot

    def _mark_interrupted(
        self,
        error_code: str,
        error_message: str = "Download worker was interrupted",
    ) -> JobRuntimeSnapshot:
        with self._lock:
            current = self._snapshot
            if is_terminal_job_state(current.state):
                return current
            self._snapshot = replace(
                current,
                state=transition_job_state(current.state, JobState.INTERRUPTED),
                error_code=error_code,
                error_message=error_message,
            )
            return self._snapshot


def _state_for_event(current: JobState, event: WorkerEnvelope) -> JobState:
    if event.event_type is WorkerEventType.CANCELLED:
        return transition_job_state(current, JobState.CANCELLED)
    if event.event_type is WorkerEventType.FAILED:
        return transition_job_state(current, JobState.FAILED)
    if event.event_type is WorkerEventType.SUCCEEDED:
        return transition_job_state(current, JobState.SUCCEEDED)

    if current is JobState.CANCELLING:
        return current

    if event.event_type is WorkerEventType.READY:
        if current in {JobState.QUEUED, JobState.RESOLVING, JobState.RUNNING}:
            return transition_job_state(current, JobState.RUNNING)
        return current
    if event.event_type is WorkerEventType.PHASE:
        phase = _optional_text(event.payload, "phase")
        if phase == "postprocessing" and current in {JobState.RUNNING, JobState.POSTPROCESSING}:
            return transition_job_state(current, JobState.POSTPROCESSING)
        if phase == "downloading" and current in {
            JobState.QUEUED,
            JobState.RESOLVING,
            JobState.RUNNING,
        }:
            return transition_job_state(current, JobState.RUNNING)
    if event.event_type is WorkerEventType.PROGRESS:
        phase = _optional_text(event.payload, "phase")
        if phase == "download" and current in {
            JobState.QUEUED,
            JobState.RESOLVING,
            JobState.RUNNING,
        }:
            return transition_job_state(current, JobState.RUNNING)

    return current


def _progress_changes(payload: Mapping[str, object]) -> dict[str, object]:
    changes: dict[str, object] = {}

    percent = _optional_number(payload, "percent")
    if percent is not None:
        changes["progress_percent"] = max(0.0, min(100.0, float(percent)))

    downloaded = _optional_non_negative_int(payload, "downloaded_bytes")
    if downloaded is not None:
        changes["downloaded_bytes"] = downloaded

    total = _optional_non_negative_int(payload, "total_bytes")
    if total is not None:
        changes["total_bytes"] = total

    speed = _optional_number(payload, "speed_bytes_per_second")
    if speed is not None and speed >= 0:
        changes["speed_bytes_per_second"] = float(speed)

    eta = _optional_number(payload, "eta_seconds")
    if eta is not None and eta >= 0:
        changes["eta_seconds"] = float(eta)

    return changes


def _optional_text(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def _optional_number(payload: Mapping[str, object], key: str) -> int | float | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _optional_non_negative_int(payload: Mapping[str, object], key: str) -> int | None:
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None
    return value


def _worker_error_message(error: DownloadWorkerError, fallback: str) -> str:
    message = str(error).strip()
    return message or fallback
