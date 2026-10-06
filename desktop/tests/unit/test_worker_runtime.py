from __future__ import annotations

from collections.abc import Callable, Mapping
from io import StringIO
from pathlib import Path
from time import sleep
from types import TracebackType
from typing import cast

import pytest

import metube_srt_desktop.worker.yt_dlp_runtime as ytdlp_runtime
from metube_srt_desktop.application.dto.download import ResolveRequest
from metube_srt_desktop.application.dto.worker_protocol import (
    WorkerCommandEnvelope,
    WorkerEnvelope,
    WorkerEventType,
    resolved_source_from_payload,
)
from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset, SourceKind
from metube_srt_desktop.worker.runtime import run_worker


class FakeYoutubeDL:
    last_options: dict[str, object] | None = None

    def __init__(self, options: dict[str, object]) -> None:
        type(self).last_options = options
        self.options = options

    def __enter__(self) -> FakeYoutubeDL:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> object:
        return False

    def extract_info(self, url: str, *, download: bool) -> object:
        if not download:
            return {
                "id": "abc",
                "title": "Video",
                "webpage_url": "https://www.youtube.com/watch?v=abc",
                "subtitles": {"id": [{"ext": "vtt"}]},
                "automatic_captions": {"en-orig": [{"ext": "vtt"}]},
            }

        sleep(0.02)
        progress_hooks = self.options.get("progress_hooks")
        assert isinstance(progress_hooks, list)
        for hook in cast(list[object], progress_hooks):
            typed_hook = _as_hook(hook)
            typed_hook(
                {
                    "status": "downloading",
                    "downloaded_bytes": 50,
                    "total_bytes": 100,
                    "speed": 10,
                    "eta": 5,
                }
            )
            typed_hook({"status": "finished"})

        postprocessor_hooks = self.options.get("postprocessor_hooks")
        assert isinstance(postprocessor_hooks, list)
        for hook in cast(list[object], postprocessor_hooks):
            _as_hook(hook)({"status": "started"})

        output_dir = self.options["paths"]
        assert isinstance(output_dir, Mapping)
        paths = cast(Mapping[str, object], output_dir)
        home = paths["home"]
        assert isinstance(home, str)
        return {
            "id": "abc",
            "title": "Video",
            "filepath": str(Path(home) / "Video [abc].mp4"),
        }


Hook = Callable[[Mapping[str, object]], None]


def _as_hook(value: object) -> Hook:
    assert callable(value)
    return cast(Hook, value)


def _events(output: StringIO) -> list[WorkerEnvelope]:
    return [WorkerEnvelope.from_json_line(line) for line in output.getvalue().splitlines()]


def test_resolve_worker_emits_typed_success_payload() -> None:
    command = WorkerCommandEnvelope.for_resolve(
        ResolveRequest("https://www.youtube.com/watch?v=abc"),
        job_id="resolve-1",
        worker_run_id="run-1",
    )
    output = StringIO()

    rc = run_worker(StringIO(command.to_json_line()), output, ydl_factory=FakeYoutubeDL)

    assert rc == 0
    events = _events(output)
    assert [event.event_type for event in events] == [
        WorkerEventType.READY,
        WorkerEventType.PHASE,
        WorkerEventType.SUCCEEDED,
    ]
    source_payload = events[-1].payload["source"]
    assert isinstance(source_payload, Mapping)
    resolved = resolved_source_from_payload(cast(Mapping[str, object], source_payload))
    assert resolved.kind is SourceKind.VIDEO
    assert resolved.items[0].video_id == "abc"


def test_download_worker_emits_progress_output_and_success(tmp_path: Path) -> None:
    job = JobSpec(
        job_id="job-1",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory=str(tmp_path),
        quality=QualityPreset.P720,
        selected_subtitle=None,
    )
    command = WorkerCommandEnvelope.for_download(job, worker_run_id="run-1")
    output = StringIO()

    rc = run_worker(StringIO(command.to_json_line()), output, ydl_factory=FakeYoutubeDL)

    assert rc == 0
    events = _events(output)
    assert events[0].event_type is WorkerEventType.READY
    assert any(event.event_type is WorkerEventType.PROGRESS for event in events)
    progress = next(event for event in events if event.event_type is WorkerEventType.PROGRESS)
    assert progress.payload["percent"] == 50.0
    output_event = next(
        event for event in events if event.event_type is WorkerEventType.OUTPUT_READY
    )
    assert str(tmp_path) in str(output_event.payload["path"])
    assert events[-1].event_type is WorkerEventType.SUCCEEDED

    assert FakeYoutubeDL.last_options is not None
    assert FakeYoutubeDL.last_options["quiet"] is True
    assert FakeYoutubeDL.last_options["noprogress"] is True
    assert FakeYoutubeDL.last_options["format_sort"] == ["res:720"]


def test_matching_cancel_control_cancels_before_download() -> None:
    job = JobSpec(
        job_id="job-1",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory="Downloads",
        quality=QualityPreset.BEST,
        selected_subtitle=None,
    )
    command = WorkerCommandEnvelope.for_download(job, worker_run_id="run-1")
    cancel = WorkerCommandEnvelope.for_cancel(job_id="job-1", worker_run_id="run-1")
    output = StringIO()

    rc = run_worker(
        StringIO(command.to_json_line() + cancel.to_json_line()),
        output,
        ydl_factory=FakeYoutubeDL,
    )

    assert rc == 0
    events = _events(output)
    assert events[-1].event_type is WorkerEventType.CANCELLED
    assert not any(event.event_type is WorkerEventType.SUCCEEDED for event in events)


def test_failure_event_does_not_echo_raw_exception_message() -> None:
    class FailingYoutubeDL(FakeYoutubeDL):
        def extract_info(self, url: str, *, download: bool) -> object:
            raise RuntimeError("https://example.test/?token=super-secret")

    command = WorkerCommandEnvelope.for_resolve(
        ResolveRequest("https://www.youtube.com/watch?v=abc"),
        job_id="resolve-1",
        worker_run_id="run-1",
    )
    output = StringIO()

    rc = run_worker(StringIO(command.to_json_line()), output, ydl_factory=FailingYoutubeDL)

    assert rc == 1
    serialized = output.getvalue()
    assert "super-secret" not in serialized
    assert _events(output)[-1].event_type is WorkerEventType.FAILED


def test_worker_classifies_youtube_login_failure_without_echoing_raw_details() -> None:
    class LoginRequiredYoutubeDL(FakeYoutubeDL):
        def extract_info(self, url: str, *, download: bool) -> object:
            raise RuntimeError(
                "ERROR: Sign in to confirm you're not a bot https://example.test/?token=do-not-echo"
            )

    command = WorkerCommandEnvelope.for_resolve(
        ResolveRequest("https://www.youtube.com/watch?v=abc"),
        job_id="resolve-login",
        worker_run_id="run-login",
    )
    output = StringIO()

    rc = run_worker(StringIO(command.to_json_line()), output, ydl_factory=LoginRequiredYoutubeDL)

    assert rc == 1
    terminal = _events(output)[-1]
    assert terminal.event_type is WorkerEventType.FAILED
    assert terminal.payload["error_code"] == "youtube_login_required"
    assert "verifikasi" in str(terminal.payload["message"]).lower()
    assert "do-not-echo" not in output.getvalue()


def test_worker_classifies_network_failure_without_raw_exception() -> None:
    class NetworkFailingYoutubeDL(FakeYoutubeDL):
        def extract_info(self, url: str, *, download: bool) -> object:
            raise RuntimeError("Unable to download webpage: connection reset by peer secret-value")

    command = WorkerCommandEnvelope.for_resolve(
        ResolveRequest("https://www.youtube.com/watch?v=abc"),
        job_id="resolve-network",
        worker_run_id="run-network",
    )
    output = StringIO()

    rc = run_worker(StringIO(command.to_json_line()), output, ydl_factory=NetworkFailingYoutubeDL)

    assert rc == 1
    terminal = _events(output)[-1]
    assert terminal.payload["error_code"] == "network_error"
    assert "secret-value" not in output.getvalue()


def test_download_progress_events_are_throttled_without_delaying_cancel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    class BurstYoutubeDL(FakeYoutubeDL):
        def extract_info(self, url: str, *, download: bool) -> object:
            if not download:
                return super().extract_info(url, download=download)

            progress_hooks = self.options.get("progress_hooks")
            assert isinstance(progress_hooks, list)
            for hook in cast(list[object], progress_hooks):
                typed_hook = _as_hook(hook)
                for downloaded in range(1, 21):
                    typed_hook(
                        {
                            "status": "downloading",
                            "downloaded_bytes": downloaded,
                            "total_bytes": 20,
                            "speed": 10,
                            "eta": 1,
                        }
                    )
                typed_hook({"status": "finished"})

            return {
                "id": "abc",
                "title": "Video",
                "filepath": str(tmp_path / "Video [abc].mp4"),
            }

    monkeypatch.setattr(ytdlp_runtime, "monotonic", lambda: 100.0)

    job = JobSpec(
        job_id="job-throttle",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory=str(tmp_path),
        quality=QualityPreset.BEST,
        selected_subtitle=None,
    )
    command = WorkerCommandEnvelope.for_download(job, worker_run_id="run-throttle")
    output = StringIO()

    rc = run_worker(StringIO(command.to_json_line()), output, ydl_factory=BurstYoutubeDL)

    assert rc == 0
    progress_events = [
        item for item in _events(output) if item.event_type is WorkerEventType.PROGRESS
    ]
    assert len(progress_events) == 1
