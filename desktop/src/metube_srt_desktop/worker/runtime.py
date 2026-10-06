from __future__ import annotations

import sys
from collections.abc import Mapping
from threading import Event, Thread
from typing import TextIO

from metube_srt_desktop.application.dto.worker_protocol import (
    WORKER_PROTOCOL_VERSION,
    WorkerCommandEnvelope,
    WorkerCommandType,
    WorkerEnvelope,
    WorkerEventType,
    resolved_source_to_payload,
)
from metube_srt_desktop.worker.yt_dlp_runtime import (
    DownloadCancellationRequested,
    YoutubeDLFactory,
    download_job_live,
    resolve_source_live,
)


class WorkerEventEmitter:
    def __init__(self, command: WorkerCommandEnvelope, stream: TextIO) -> None:
        self._job_id = command.job_id
        self._worker_run_id = command.worker_run_id
        self._stream = stream
        self._sequence = 0

    def emit(self, event_type: WorkerEventType, payload: Mapping[str, object]) -> None:
        event = WorkerEnvelope(
            schema_version=WORKER_PROTOCOL_VERSION,
            event_type=event_type,
            job_id=self._job_id,
            worker_run_id=self._worker_run_id,
            sequence=self._sequence,
            payload=payload,
        )
        self._sequence += 1
        self._stream.write(event.to_json_line())
        self._stream.flush()


def run_worker(
    stdin: TextIO,
    stdout: TextIO,
    *,
    ydl_factory: YoutubeDLFactory | None = None,
) -> int:
    """Run exactly one resolve/download operation in this child process."""

    first_line = stdin.readline()
    if not first_line:
        return 2

    try:
        command = WorkerCommandEnvelope.from_json_line(first_line)
    except (ValueError, TypeError, KeyError):
        return 2

    emitter = WorkerEventEmitter(command, stdout)
    emitter.emit(WorkerEventType.READY, {"mode": command.command_type.value})

    cancellation = Event()
    if command.command_type is WorkerCommandType.CANCEL:
        emitter.emit(WorkerEventType.CANCELLED, {"reason": "requested_before_start"})
        return 0

    _start_cancel_monitor(stdin, command, cancellation)

    try:
        if command.command_type is WorkerCommandType.RESOLVE:
            emitter.emit(WorkerEventType.PHASE, {"phase": "resolving"})
            source = resolve_source_live(command.as_resolve_request(), ydl_factory=ydl_factory)
            if cancellation.is_set():
                raise DownloadCancellationRequested
            emitter.emit(
                WorkerEventType.SUCCEEDED,
                {"mode": "resolve", "source": resolved_source_to_payload(source)},
            )
            return 0

        if command.command_type is WorkerCommandType.DOWNLOAD:
            emitter.emit(WorkerEventType.PHASE, {"phase": "downloading"})
            outputs = download_job_live(
                command.as_job_spec(),
                cancellation=cancellation,
                emit=emitter.emit,
                ydl_factory=ydl_factory,
            )
            for output_path in outputs:
                emitter.emit(WorkerEventType.OUTPUT_READY, {"path": output_path})
            emitter.emit(
                WorkerEventType.SUCCEEDED,
                {"mode": "download", "output_count": len(outputs)},
            )
            return 0

        emitter.emit(
            WorkerEventType.FAILED,
            {"error_code": "unsupported_command", "message": "Unsupported worker command"},
        )
        return 1
    except DownloadCancellationRequested:
        emitter.emit(WorkerEventType.CANCELLED, {"reason": "requested"})
        return 0
    except ValueError:
        emitter.emit(
            WorkerEventType.FAILED,
            {
                "error_code": "metadata_validation",
                "message": "Worker input or extracted metadata failed validation",
            },
        )
        return 1
    except OSError:
        emitter.emit(
            WorkerEventType.FAILED,
            {
                "error_code": "io_error",
                "message": "Download worker could not access a required local resource",
            },
        )
        return 1
    except Exception:
        emitter.emit(
            WorkerEventType.FAILED,
            {"error_code": "yt_dlp_error", "message": "yt-dlp operation failed"},
        )
        return 1


def _start_cancel_monitor(
    stdin: TextIO,
    command: WorkerCommandEnvelope,
    cancellation: Event,
) -> Thread:
    def monitor() -> None:
        for line in stdin:
            try:
                control = WorkerCommandEnvelope.from_json_line(line)
            except (ValueError, TypeError, KeyError):
                continue
            if (
                control.command_type is WorkerCommandType.CANCEL
                and control.job_id == command.job_id
                and control.worker_run_id == command.worker_run_id
            ):
                cancellation.set()
                return

    thread = Thread(target=monitor, name="worker-cancel-monitor", daemon=True)
    thread.start()
    return thread


def main() -> int:
    return run_worker(sys.stdin, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
