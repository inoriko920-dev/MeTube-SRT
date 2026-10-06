from __future__ import annotations

import subprocess
from collections.abc import Sequence
from io import StringIO
from threading import Event
from typing import TextIO

import pytest

from metube_srt_desktop.adapters.download import (
    SubprocessWorkerAdapter,
    WorkerProcessError,
    WorkerProtocolError,
)
from metube_srt_desktop.application.dto.worker_protocol import (
    WORKER_PROTOCOL_VERSION,
    WorkerCommandEnvelope,
    WorkerEnvelope,
    WorkerEventType,
)
from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset


class CapturingInput(StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.was_closed = False

    def close(self) -> None:
        self.was_closed = True


class FakeProcess:
    def __init__(
        self,
        output: str,
        *,
        return_code: int = 0,
        timeout_until_killed: bool = False,
    ) -> None:
        self.stdin_buffer = CapturingInput()
        self.stdin: TextIO | None = self.stdin_buffer
        self.stdout: TextIO | None = StringIO(output)
        self.return_code = return_code
        self.timeout_until_killed = timeout_until_killed
        self.terminated = False
        self.killed = False
        self.kill_event = Event()

    def poll(self) -> int | None:
        if self.timeout_until_killed and not self.killed:
            return None
        return self.return_code

    def wait(self, timeout: float | None = None) -> int:
        if self.timeout_until_killed and not self.killed:
            if timeout is None:
                return self.return_code
            raise subprocess.TimeoutExpired(cmd="fake-worker", timeout=timeout)
        return self.return_code

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True
        self.kill_event.set()


class CapturingFactory:
    def __init__(self, process: FakeProcess) -> None:
        self.process = process
        self.argv: tuple[str, ...] | None = None

    def __call__(self, argv: Sequence[str]) -> FakeProcess:
        self.argv = tuple(argv)
        return self.process


def event_line(
    event_type: WorkerEventType,
    *,
    sequence: int,
    job_id: str = "job-1",
    worker_run_id: str = "run-1",
) -> str:
    return WorkerEnvelope(
        schema_version=WORKER_PROTOCOL_VERSION,
        event_type=event_type,
        job_id=job_id,
        worker_run_id=worker_run_id,
        sequence=sequence,
        payload={},
    ).to_json_line()


def make_download_command() -> WorkerCommandEnvelope:
    job = JobSpec(
        job_id="job-1",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory="Downloads",
        quality=QualityPreset.BEST,
        selected_subtitle=None,
    )
    return WorkerCommandEnvelope.for_download(job, worker_run_id="run-1")


def test_adapter_writes_command_and_yields_ordered_events() -> None:
    process = FakeProcess(
        event_line(WorkerEventType.READY, sequence=0)
        + event_line(WorkerEventType.PHASE, sequence=1)
        + event_line(WorkerEventType.SUCCEEDED, sequence=2)
    )
    factory = CapturingFactory(process)
    adapter = SubprocessWorkerAdapter(
        make_download_command(),
        worker_argv=("python", "-m", "metube_srt_desktop.worker"),
        process_factory=factory,
    )

    events = list(adapter.events())

    assert [event.event_type for event in events] == [
        WorkerEventType.READY,
        WorkerEventType.PHASE,
        WorkerEventType.SUCCEEDED,
    ]
    assert factory.argv == ("python", "-m", "metube_srt_desktop.worker")
    written = process.stdin_buffer.getvalue()
    assert WorkerCommandEnvelope.from_json_line(written).command_type.value == "download"
    assert process.stdin_buffer.was_closed is True


def test_stale_worker_run_event_is_ignored() -> None:
    process = FakeProcess(
        event_line(
            WorkerEventType.READY,
            sequence=99,
            worker_run_id="old-run",
        )
        + event_line(WorkerEventType.READY, sequence=0)
        + event_line(WorkerEventType.SUCCEEDED, sequence=1)
    )
    adapter = SubprocessWorkerAdapter(
        make_download_command(),
        process_factory=CapturingFactory(process),
    )

    events = list(adapter.events())

    assert [event.sequence for event in events] == [0, 1]


def test_sequence_gap_is_rejected_and_process_is_terminated() -> None:
    process = FakeProcess(
        event_line(WorkerEventType.READY, sequence=0)
        + event_line(WorkerEventType.SUCCEEDED, sequence=2),
        timeout_until_killed=True,
    )
    adapter = SubprocessWorkerAdapter(
        make_download_command(),
        process_factory=CapturingFactory(process),
        terminate_grace_seconds=0,
    )

    with pytest.raises(WorkerProtocolError, match="sequence"):
        list(adapter.events())

    assert process.terminated is True
    assert process.killed is True


def test_missing_terminal_event_is_reported() -> None:
    process = FakeProcess(event_line(WorkerEventType.READY, sequence=0))
    adapter = SubprocessWorkerAdapter(
        make_download_command(),
        process_factory=CapturingFactory(process),
    )

    with pytest.raises(WorkerProcessError, match="without a terminal"):
        list(adapter.events())


def test_failed_terminal_event_allows_worker_error_exit_code() -> None:
    process = FakeProcess(
        event_line(WorkerEventType.READY, sequence=0)
        + event_line(WorkerEventType.FAILED, sequence=1),
        return_code=1,
    )
    adapter = SubprocessWorkerAdapter(
        make_download_command(),
        process_factory=CapturingFactory(process),
    )

    events = list(adapter.events())

    assert events[-1].event_type is WorkerEventType.FAILED


def test_request_cancel_writes_control_and_escalates_without_blocking() -> None:
    process = FakeProcess("", timeout_until_killed=True)
    adapter = SubprocessWorkerAdapter(
        make_download_command(),
        process_factory=CapturingFactory(process),
        cancel_grace_seconds=0,
        terminate_grace_seconds=0,
    )

    adapter.request_cancel()

    assert process.kill_event.wait(1.0)
    commands = [
        WorkerCommandEnvelope.from_json_line(line)
        for line in process.stdin_buffer.getvalue().splitlines()
    ]
    assert [command.command_type.value for command in commands] == ["download", "cancel"]
    assert process.terminated is True
    assert process.killed is True


def test_real_child_process_cancel_command_contract() -> None:
    command = WorkerCommandEnvelope.for_cancel(job_id="job-1", worker_run_id="run-1")
    adapter = SubprocessWorkerAdapter(command)

    events = list(adapter.events())

    assert [event.event_type for event in events] == [
        WorkerEventType.READY,
        WorkerEventType.CANCELLED,
    ]
