from __future__ import annotations

from collections.abc import Sequence
from io import StringIO
from typing import TextIO

import pytest

from metube_srt_desktop.adapters.download import SubprocessSourceResolver
from metube_srt_desktop.application.dto.download import (
    ResolvedItem,
    ResolvedSource,
    ResolveRequest,
)
from metube_srt_desktop.application.dto.worker_protocol import (
    WORKER_PROTOCOL_VERSION,
    WorkerCommandEnvelope,
    WorkerCommandType,
    WorkerEnvelope,
    WorkerEventType,
    resolved_source_to_payload,
)
from metube_srt_desktop.application.ports.source_resolver import SourceResolveError
from metube_srt_desktop.domain.jobs import SourceKind


class CapturingInput(StringIO):
    def __init__(self) -> None:
        super().__init__()
        self.was_closed = False

    def close(self) -> None:
        self.was_closed = True


class FakeProcess:
    def __init__(self, output: str, *, return_code: int = 0) -> None:
        self.stdin_buffer = CapturingInput()
        self.stdin: TextIO | None = self.stdin_buffer
        self.stdout: TextIO | None = StringIO(output)
        self.return_code = return_code
        self.terminated = False
        self.killed = False

    def poll(self) -> int | None:
        return self.return_code

    def wait(self, timeout: float | None = None) -> int:
        return self.return_code

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


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
    payload: dict[str, object] | None = None,
) -> str:
    return WorkerEnvelope(
        schema_version=WORKER_PROTOCOL_VERSION,
        event_type=event_type,
        job_id="resolve-1",
        worker_run_id="run-1",
        sequence=sequence,
        payload={} if payload is None else payload,
    ).to_json_line()


def make_source() -> ResolvedSource:
    return ResolvedSource(
        source_url="https://www.youtube.com/playlist?list=PL123",
        kind=SourceKind.PLAYLIST,
        title="Playlist",
        items=(
            ResolvedItem(
                video_id="a",
                title="A",
                webpage_url="https://www.youtube.com/watch?v=a",
            ),
            ResolvedItem(
                video_id="b",
                title="B",
                webpage_url="https://www.youtube.com/watch?v=b",
            ),
        ),
    )


def test_subprocess_source_resolver_returns_typed_metadata() -> None:
    source = make_source()
    process = FakeProcess(
        event_line(WorkerEventType.READY, sequence=0, payload={"mode": "resolve"})
        + event_line(WorkerEventType.PHASE, sequence=1, payload={"phase": "resolving"})
        + event_line(
            WorkerEventType.SUCCEEDED,
            sequence=2,
            payload={"mode": "resolve", "source": resolved_source_to_payload(source)},
        )
    )
    factory = CapturingFactory(process)
    resolver = SubprocessSourceResolver(
        worker_argv=("python", "-m", "metube_srt_desktop.worker"),
        process_factory=factory,
        resolve_id_factory=lambda: "resolve-1",
        worker_run_id_factory=lambda: "run-1",
    )

    resolved = resolver.resolve(ResolveRequest(source.source_url))

    assert resolved == source
    assert factory.argv == ("python", "-m", "metube_srt_desktop.worker")
    command = WorkerCommandEnvelope.from_json_line(process.stdin_buffer.getvalue())
    assert command.command_type is WorkerCommandType.RESOLVE
    assert command.as_resolve_request() == ResolveRequest(source.source_url)
    assert process.stdin_buffer.was_closed is True


def test_worker_failed_event_becomes_application_source_resolve_error() -> None:
    process = FakeProcess(
        event_line(WorkerEventType.READY, sequence=0)
        + event_line(
            WorkerEventType.FAILED,
            sequence=1,
            payload={
                "error_code": "metadata_validation",
                "message": "Worker input or extracted metadata failed validation",
            },
        ),
        return_code=1,
    )
    resolver = SubprocessSourceResolver(
        process_factory=CapturingFactory(process),
        resolve_id_factory=lambda: "resolve-1",
        worker_run_id_factory=lambda: "run-1",
    )

    with pytest.raises(SourceResolveError) as caught:
        resolver.resolve(ResolveRequest("https://www.youtube.com/watch?v=abc"))

    assert caught.value.error_code == "metadata_validation"
    assert "metadata" in caught.value.message.lower()


def test_protocol_corruption_is_mapped_to_sanitized_resolve_error() -> None:
    process = FakeProcess(
        event_line(WorkerEventType.READY, sequence=0)
        + event_line(WorkerEventType.SUCCEEDED, sequence=2)
    )
    resolver = SubprocessSourceResolver(
        process_factory=CapturingFactory(process),
        resolve_id_factory=lambda: "resolve-1",
        worker_run_id_factory=lambda: "run-1",
    )

    with pytest.raises(SourceResolveError) as caught:
        resolver.resolve(ResolveRequest("https://www.youtube.com/watch?v=abc"))

    assert caught.value.error_code == "worker_process_failed"
    assert caught.value.message == "Source resolve worker failed"


def test_invalid_success_payload_is_rejected() -> None:
    process = FakeProcess(
        event_line(WorkerEventType.READY, sequence=0)
        + event_line(
            WorkerEventType.SUCCEEDED,
            sequence=1,
            payload={"mode": "download", "source": {}},
        )
    )
    resolver = SubprocessSourceResolver(
        process_factory=CapturingFactory(process),
        resolve_id_factory=lambda: "resolve-1",
        worker_run_id_factory=lambda: "run-1",
    )

    with pytest.raises(SourceResolveError, match="invalid result") as caught:
        resolver.resolve(ResolveRequest("https://www.youtube.com/watch?v=abc"))

    assert caught.value.error_code == "invalid_resolve_payload"


class RunningFakeProcess(FakeProcess):
    def poll(self) -> int | None:
        return None


def test_cancel_before_worker_registration_is_applied_to_next_resolve() -> None:
    process = RunningFakeProcess(
        event_line(WorkerEventType.READY, sequence=0)
        + event_line(
            WorkerEventType.CANCELLED,
            sequence=1,
            payload={"reason": "requested"},
        )
    )
    resolver = SubprocessSourceResolver(
        process_factory=CapturingFactory(process),
        resolve_id_factory=lambda: "resolve-1",
        worker_run_id_factory=lambda: "run-1",
    )

    resolver.cancel_current()

    with pytest.raises(SourceResolveError) as caught:
        resolver.resolve(ResolveRequest("https://www.youtube.com/watch?v=abc"))

    assert caught.value.error_code == "resolve_cancelled"
    commands = [
        WorkerCommandEnvelope.from_json_line(line)
        for line in process.stdin_buffer.getvalue().splitlines()
    ]
    assert [command.command_type for command in commands] == [
        WorkerCommandType.RESOLVE,
        WorkerCommandType.CANCEL,
    ]
