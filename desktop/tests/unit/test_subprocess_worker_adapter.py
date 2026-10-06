from __future__ import annotations

import subprocess
from collections.abc import Sequence
from io import StringIO
from threading import Event, Thread
from typing import TextIO

import pytest

from metube_srt_desktop.adapters.download import (
    SubprocessWorkerAdapter,
    WorkerProcessError,
    WorkerProtocolError,
)
from metube_srt_desktop.adapters.download.subprocess_worker import (
    worker_process_environment,
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


class SlowCleanExitProcess(FakeProcess):
    def __init__(self, output: str, *, minimum_clean_timeout: float) -> None:
        super().__init__(output)
        self.minimum_clean_timeout = minimum_clean_timeout
        self.wait_timeouts: list[float | None] = []

    def wait(self, timeout: float | None = None) -> int:
        self.wait_timeouts.append(timeout)
        if timeout is not None and timeout < self.minimum_clean_timeout:
            raise subprocess.TimeoutExpired(cmd="fake-worker", timeout=timeout)
        return 0


def test_terminal_event_allows_packaged_worker_time_to_exit_cleanly() -> None:
    process = SlowCleanExitProcess(
        event_line(WorkerEventType.READY, sequence=0)
        + event_line(WorkerEventType.SUCCEEDED, sequence=1),
        minimum_clean_timeout=3.0,
    )
    adapter = SubprocessWorkerAdapter(
        make_download_command(),
        process_factory=CapturingFactory(process),
        terminate_grace_seconds=0.1,
        terminal_exit_grace_seconds=5.0,
    )

    events = list(adapter.events())

    assert events[-1].event_type is WorkerEventType.SUCCEEDED
    assert 5.0 in process.wait_timeouts
    assert process.terminated is False
    assert process.killed is False


def test_initial_command_is_published_before_concurrent_cancel() -> None:
    class BlockingFirstWrite(CapturingInput):
        def __init__(self) -> None:
            super().__init__()
            self.first_write_started = Event()
            self.release_first_write = Event()
            self.write_count = 0

        def write(self, value: str) -> int:
            self.write_count += 1
            if self.write_count == 1:
                self.first_write_started.set()
                assert self.release_first_write.wait(1.0)
            return super().write(value)

    process = FakeProcess("", timeout_until_killed=True)
    blocking_input = BlockingFirstWrite()
    process.stdin_buffer = blocking_input
    process.stdin = blocking_input
    adapter = SubprocessWorkerAdapter(
        make_download_command(),
        process_factory=CapturingFactory(process),
        cancel_grace_seconds=0,
        terminate_grace_seconds=0,
    )

    event_error: list[BaseException] = []

    def consume_events() -> None:
        try:
            list(adapter.events())
        except BaseException as exc:
            event_error.append(exc)

    consumer = Thread(target=consume_events)
    consumer.start()
    assert blocking_input.first_write_started.wait(1.0)

    cancel_thread = Thread(target=adapter.request_cancel)
    cancel_thread.start()

    # Cancel cannot publish while the initial command is still being written.
    assert blocking_input.write_count == 1
    blocking_input.release_first_write.set()

    cancel_thread.join(1.0)
    consumer.join(1.0)

    commands = [
        WorkerCommandEnvelope.from_json_line(line)
        for line in blocking_input.getvalue().splitlines()
    ]
    assert commands
    assert commands[0].command_type.value == "download"


def test_missing_terminal_stream_close_does_not_wait_forever() -> None:
    process = FakeProcess(
        event_line(WorkerEventType.READY, sequence=0),
        timeout_until_killed=True,
    )
    adapter = SubprocessWorkerAdapter(
        make_download_command(),
        process_factory=CapturingFactory(process),
        terminate_grace_seconds=0,
    )

    with pytest.raises(WorkerProcessError, match="event stream"):
        list(adapter.events())

    assert process.terminated is True
    assert process.killed is True



def test_worker_process_environment_forces_utf8_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONUTF8", "0")
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")

    environment = worker_process_environment()

    assert environment["PYTHONUTF8"] == "1"
    assert environment["PYTHONIOENCODING"] == "utf-8"
