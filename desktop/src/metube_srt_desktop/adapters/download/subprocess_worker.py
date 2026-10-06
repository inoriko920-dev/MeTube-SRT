from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from threading import Lock, RLock, Thread
from typing import Protocol, TextIO, cast
from uuid import uuid4

from metube_srt_desktop.application.dto.download import ResolvedSource, ResolveRequest
from metube_srt_desktop.application.dto.worker_protocol import (
    WorkerCommandEnvelope,
    WorkerEnvelope,
    WorkerEventType,
    resolved_source_from_payload,
)
from metube_srt_desktop.application.ports.download_worker import (
    DownloadWorkerError,
    DownloadWorkerFactoryPort,
    DownloadWorkerPort,
)
from metube_srt_desktop.application.ports.source_resolver import (
    SourceResolveError,
    SourceResolverPort,
)
from metube_srt_desktop.domain.jobs import JobSpec

_TERMINAL_EVENTS = {
    WorkerEventType.SUCCEEDED,
    WorkerEventType.FAILED,
    WorkerEventType.CANCELLED,
}


class WorkerAdapterError(DownloadWorkerError):
    """Base error for parent-side worker process failures."""


class WorkerProtocolError(WorkerAdapterError):
    """Raised when the child process violates the typed IPC contract."""


class WorkerProcessError(WorkerAdapterError):
    """Raised when the worker exits without a valid terminal protocol event."""


class WorkerProcess(Protocol):
    stdin: TextIO | None
    stdout: TextIO | None

    def poll(self) -> int | None: ...

    def wait(self, timeout: float | None = None) -> int: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...


ProcessFactory = Callable[[Sequence[str]], WorkerProcess]


def _default_worker_argv() -> tuple[str, ...]:
    override = os.environ.get("METUBE_SRT_WORKER_EXE", "").strip()
    if override:
        return (override,)

    if getattr(sys, "frozen", False):
        worker = Path(sys.executable).resolve().with_name("MeTube-SRT-Worker.exe")
        return (str(worker),)

    return (sys.executable, "-m", "metube_srt_desktop.worker")


def _default_process_factory(argv: Sequence[str]) -> WorkerProcess:
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    process = subprocess.Popen(
        list(argv),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="strict",
        bufsize=1,
        creationflags=creationflags,
    )
    return cast(WorkerProcess, process)


class SubprocessWorkerAdapter(DownloadWorkerPort):
    """Parent-side owner of one disposable child-worker run.

    This boundary owns process lifecycle and IPC only. It does not own Qt state,
    queue persistence, or canonical job state.
    """

    def __init__(
        self,
        command: WorkerCommandEnvelope,
        *,
        worker_argv: Sequence[str] | None = None,
        process_factory: ProcessFactory | None = None,
        cancel_grace_seconds: float = 2.0,
        terminate_grace_seconds: float = 1.0,
    ) -> None:
        if cancel_grace_seconds < 0:
            raise ValueError("cancel_grace_seconds must be >= 0")
        if terminate_grace_seconds < 0:
            raise ValueError("terminate_grace_seconds must be >= 0")

        self._command = command
        self._worker_argv = tuple(
            worker_argv if worker_argv is not None else _default_worker_argv()
        )
        if not self._worker_argv:
            raise ValueError("worker_argv must not be empty")

        self._process_factory = process_factory or _default_process_factory
        self._cancel_grace_seconds = cancel_grace_seconds
        self._terminate_grace_seconds = terminate_grace_seconds

        self._process: WorkerProcess | None = None
        self._write_lock = RLock()
        self._state_lock = Lock()
        self._events_claimed = False
        self._cancel_watchdog_started = False
        self._terminal_seen = False

    def events(self) -> Iterable[WorkerEnvelope]:
        with self._state_lock:
            if self._events_claimed:
                raise RuntimeError("worker events can only be consumed once")
            self._events_claimed = True

        process = self._ensure_started()
        stdout = process.stdout
        if stdout is None:
            self._abort_process(process)
            raise WorkerProcessError("worker stdout pipe is unavailable")

        expected_sequence = 0
        terminal_event: WorkerEnvelope | None = None

        try:
            for line in stdout:
                try:
                    event = WorkerEnvelope.from_json_line(line)
                except (ValueError, TypeError, KeyError) as exc:
                    raise WorkerProtocolError("worker emitted malformed protocol data") from exc

                if (
                    event.job_id != self._command.job_id
                    or event.worker_run_id != self._command.worker_run_id
                ):
                    continue

                if event.sequence != expected_sequence:
                    raise WorkerProtocolError("worker event sequence is not contiguous")
                expected_sequence += 1

                yield event
                if event.event_type in _TERMINAL_EVENTS:
                    terminal_event = event
                    with self._state_lock:
                        self._terminal_seen = True
                    break
        except GeneratorExit:
            self._abort_process(process)
            raise
        except BaseException:
            self._abort_process(process)
            raise
        finally:
            if terminal_event is not None:
                self._close_stdin(process)

        if terminal_event is None:
            return_code = process.wait()
            raise WorkerProcessError(f"worker exited without a terminal event (code {return_code})")

        return_code = self._wait_after_terminal(process)
        if terminal_event.event_type is WorkerEventType.FAILED:
            return
        if return_code != 0:
            raise WorkerProcessError(f"worker exited with code {return_code} after terminal event")

    def request_cancel(self) -> None:
        """Send cooperative cancellation and escalate asynchronously if required."""

        with self._state_lock:
            if self._terminal_seen:
                return

        process = self._ensure_started()
        if process.poll() is not None:
            return

        cancel_command = WorkerCommandEnvelope.for_cancel(
            job_id=self._command.job_id,
            worker_run_id=self._command.worker_run_id,
        )
        self._write_command(process, cancel_command)

        with self._state_lock:
            if self._cancel_watchdog_started:
                return
            self._cancel_watchdog_started = True

        Thread(
            target=self._cancel_watchdog,
            args=(process,),
            name="worker-cancel-watchdog",
            daemon=True,
        ).start()

    def _ensure_started(self) -> WorkerProcess:
        with self._state_lock:
            existing = self._process
            if existing is not None:
                return existing
            try:
                process = self._process_factory(self._worker_argv)
            except OSError as exc:
                raise WorkerProcessError("worker process could not be started") from exc
            self._process = process

        self._write_command(process, self._command)
        return process

    def _write_command(
        self,
        process: WorkerProcess,
        command: WorkerCommandEnvelope,
    ) -> None:
        stdin = process.stdin
        if stdin is None:
            self._abort_process(process)
            raise WorkerProcessError("worker stdin pipe is unavailable")

        try:
            with self._write_lock:
                stdin.write(command.to_json_line())
                stdin.flush()
        except (BrokenPipeError, OSError, ValueError) as exc:
            self._abort_process(process)
            raise WorkerProcessError("worker command pipe is unavailable") from exc

    def _wait_after_terminal(self, process: WorkerProcess) -> int:
        try:
            return process.wait(timeout=self._terminate_grace_seconds)
        except subprocess.TimeoutExpired as exc:
            self._abort_process(process)
            raise WorkerProcessError("worker did not exit after terminal event") from exc

    def _cancel_watchdog(self, process: WorkerProcess) -> None:
        try:
            process.wait(timeout=self._cancel_grace_seconds)
            return
        except subprocess.TimeoutExpired:
            pass

        try:
            process.terminate()
        except OSError:
            return

        try:
            process.wait(timeout=self._terminate_grace_seconds)
            return
        except subprocess.TimeoutExpired:
            pass

        try:
            process.kill()
        except OSError:
            return

    def _abort_process(self, process: WorkerProcess) -> None:
        self._close_stdin(process)
        if process.poll() is not None:
            return
        try:
            process.terminate()
        except OSError:
            return
        try:
            process.wait(timeout=self._terminate_grace_seconds)
            return
        except subprocess.TimeoutExpired:
            pass
        try:
            process.kill()
        except OSError:
            return
        with suppress(OSError, subprocess.TimeoutExpired):
            process.wait(timeout=self._terminate_grace_seconds)

    def _close_stdin(self, process: WorkerProcess) -> None:
        stdin = process.stdin
        if stdin is None:
            return
        with self._write_lock, suppress(OSError, ValueError):
            stdin.close()


class SubprocessDownloadWorkerFactory(DownloadWorkerFactoryPort):
    """Construct lazy subprocess workers for application-owned download jobs."""

    def __init__(
        self,
        *,
        worker_argv: Sequence[str] | None = None,
        cancel_grace_seconds: float = 2.0,
        terminate_grace_seconds: float = 1.0,
    ) -> None:
        self._worker_argv = None if worker_argv is None else tuple(worker_argv)
        self._cancel_grace_seconds = cancel_grace_seconds
        self._terminate_grace_seconds = terminate_grace_seconds

    def create(
        self,
        job: JobSpec,
        *,
        worker_run_id: str,
    ) -> DownloadWorkerPort:
        command = WorkerCommandEnvelope.for_download(job, worker_run_id=worker_run_id)
        return SubprocessWorkerAdapter(
            command,
            worker_argv=self._worker_argv,
            cancel_grace_seconds=self._cancel_grace_seconds,
            terminate_grace_seconds=self._terminate_grace_seconds,
        )


def _new_resolve_id() -> str:
    return f"resolve-{uuid4().hex}"


def _new_resolve_run_id() -> str:
    return uuid4().hex


class SubprocessSourceResolver(SourceResolverPort):
    """Resolve metadata through the same isolated worker protocol as downloads."""

    def __init__(
        self,
        *,
        worker_argv: Sequence[str] | None = None,
        process_factory: ProcessFactory | None = None,
        resolve_id_factory: Callable[[], str] = _new_resolve_id,
        worker_run_id_factory: Callable[[], str] = _new_resolve_run_id,
        terminate_grace_seconds: float = 1.0,
    ) -> None:
        self._worker_argv = None if worker_argv is None else tuple(worker_argv)
        self._process_factory = process_factory
        self._resolve_id_factory = resolve_id_factory
        self._worker_run_id_factory = worker_run_id_factory
        self._terminate_grace_seconds = terminate_grace_seconds

    def resolve(self, request: ResolveRequest) -> ResolvedSource:
        resolve_id = self._resolve_id_factory()
        worker_run_id = self._worker_run_id_factory()
        if not resolve_id.strip():
            raise ValueError("resolve_id_factory returned an empty value")
        if not worker_run_id.strip():
            raise ValueError("worker_run_id_factory returned an empty value")

        command = WorkerCommandEnvelope.for_resolve(
            request,
            job_id=resolve_id,
            worker_run_id=worker_run_id,
        )
        worker = SubprocessWorkerAdapter(
            command,
            worker_argv=self._worker_argv,
            process_factory=self._process_factory,
            terminate_grace_seconds=self._terminate_grace_seconds,
        )

        try:
            events = tuple(worker.events())
        except WorkerAdapterError as exc:
            raise SourceResolveError(
                "worker_process_failed",
                "Source resolve worker failed",
            ) from exc

        if not events:
            raise SourceResolveError(
                "worker_protocol_failed",
                "Source resolve worker returned no terminal event",
            )

        terminal = events[-1]
        if terminal.event_type is WorkerEventType.FAILED:
            raise SourceResolveError(
                _payload_text(terminal.payload, "error_code") or "resolve_failed",
                _payload_text(terminal.payload, "message") or "Source resolve failed",
            )
        if terminal.event_type is WorkerEventType.CANCELLED:
            raise SourceResolveError(
                "resolve_cancelled",
                "Source resolve was cancelled",
            )
        if terminal.event_type is not WorkerEventType.SUCCEEDED:
            raise SourceResolveError(
                "worker_protocol_failed",
                "Source resolve worker ended without success",
            )
        if _payload_text(terminal.payload, "mode") != "resolve":
            raise SourceResolveError(
                "invalid_resolve_payload",
                "Source resolve worker returned an invalid result",
            )

        source_payload = terminal.payload.get("source")
        if not isinstance(source_payload, Mapping):
            raise SourceResolveError(
                "invalid_resolve_payload",
                "Source resolve worker returned an invalid result",
            )

        try:
            return resolved_source_from_payload(cast(Mapping[str, object], source_payload))
        except (ValueError, TypeError, KeyError) as exc:
            raise SourceResolveError(
                "invalid_resolve_payload",
                "Source resolve worker returned invalid metadata",
            ) from exc


def _payload_text(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        return None
    return value
