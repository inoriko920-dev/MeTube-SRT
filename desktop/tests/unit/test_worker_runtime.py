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
from metube_srt_desktop.domain.subtitles import SubtitleKind, SubtitleTrack
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
        output_path = Path(home) / "Video [abc].mp4"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"video")
        return {
            "id": "abc",
            "title": "Video",
            "filepath": str(output_path),
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

            output_path = tmp_path / "Video [abc].mp4"
            output_path.write_bytes(b"video")
            return {
                "id": "abc",
                "title": "Video",
                "filepath": str(output_path),
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
    assert len(progress_events) == 2
    assert progress_events[-1].payload["percent"] == 100.0


def test_runtime_entrypoint_is_after_failure_classifier() -> None:
    from pathlib import Path

    import metube_srt_desktop.worker.runtime as runtime_module

    source = Path(runtime_module.__file__).read_text(encoding="utf-8")
    classifier_index = source.index("def _classify_runtime_failure")
    entrypoint_index = source.index('if __name__ == "__main__"')

    assert classifier_index < entrypoint_index


def test_subtitle_failure_warns_but_keeps_successful_video(tmp_path: Path) -> None:
    class SubtitleFailYoutubeDL(FakeYoutubeDL):
        calls = 0

        def extract_info(self, url: str, *, download: bool) -> object:
            type(self).calls += 1
            if self.options.get("skip_download") is True:
                raise RuntimeError("subtitle provider failed")
            return super().extract_info(url, download=download)

    SubtitleFailYoutubeDL.calls = 0
    job = JobSpec(
        job_id="job-subtitle-fallback",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory=str(tmp_path),
        quality=QualityPreset.BEST,
        selected_subtitle=SubtitleTrack(
            language_code="id",
            kind=SubtitleKind.MANUAL,
            is_original=True,
        ),
    )
    command = WorkerCommandEnvelope.for_download(job, worker_run_id="run-subtitle-fallback")
    output = StringIO()

    rc = run_worker(
        StringIO(command.to_json_line()),
        output,
        ydl_factory=SubtitleFailYoutubeDL,
    )

    assert rc == 0
    events = _events(output)
    assert SubtitleFailYoutubeDL.calls == 2
    assert any(event.event_type is WorkerEventType.WARNING for event in events)
    assert events[-1].event_type is WorkerEventType.SUCCEEDED
    warning = next(event for event in events if event.event_type is WorkerEventType.WARNING)
    assert "video tetap disimpan" in str(warning.payload["message"]).lower()


def test_subtitle_only_metadata_cannot_announce_fake_media_path(tmp_path: Path) -> None:
    class MissingSubtitleYoutubeDL(FakeYoutubeDL):
        def extract_info(self, url: str, *, download: bool) -> object:
            if self.options.get("skip_download") is True:
                return {
                    "id": "abc",
                    "title": "Video",
                    "_filename": str(tmp_path / "never-downloaded.mp4"),
                    "requested_subtitles": {},
                }
            media = tmp_path / "actual.webm"
            media.write_bytes(b"video")
            return {
                "id": "abc",
                "title": "Video",
                "filepath": str(media),
            }

    job = JobSpec(
        job_id="job-no-srt",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory=str(tmp_path),
        quality=QualityPreset.BEST,
        selected_subtitle=SubtitleTrack(
            language_code="id",
            kind=SubtitleKind.MANUAL,
            is_original=True,
        ),
    )
    command = WorkerCommandEnvelope.for_download(job, worker_run_id="run-no-srt")
    output = StringIO()

    rc = run_worker(StringIO(command.to_json_line()), output, ydl_factory=MissingSubtitleYoutubeDL)

    assert rc == 0
    events = _events(output)
    output_paths = [
        str(event.payload["path"])
        for event in events
        if event.event_type is WorkerEventType.OUTPUT_READY
    ]
    assert output_paths == [str(tmp_path / "actual.webm")]
    assert not any("never-downloaded.mp4" in path for path in output_paths)
    assert any(event.event_type is WorkerEventType.WARNING for event in events)


def test_missing_media_file_fails_instead_of_reporting_success(tmp_path: Path) -> None:
    class MissingMediaYoutubeDL(FakeYoutubeDL):
        def extract_info(self, url: str, *, download: bool) -> object:
            return {
                "id": "abc",
                "title": "Video",
                "filepath": str(tmp_path / "does-not-exist.mp4"),
            }

    job = JobSpec(
        job_id="job-missing-media",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory=str(tmp_path),
        quality=QualityPreset.BEST,
        selected_subtitle=None,
    )
    command = WorkerCommandEnvelope.for_download(job, worker_run_id="run-missing-media")
    output = StringIO()

    rc = run_worker(StringIO(command.to_json_line()), output, ydl_factory=MissingMediaYoutubeDL)

    assert rc == 1
    events = _events(output)
    assert not any(event.event_type is WorkerEventType.OUTPUT_READY for event in events)
    assert events[-1].event_type is WorkerEventType.FAILED
    assert events[-1].payload["error_code"] == "output_missing"


def test_existing_srt_is_announced_with_media_without_warning(tmp_path: Path) -> None:
    class SubtitleYoutubeDL(FakeYoutubeDL):
        def extract_info(self, url: str, *, download: bool) -> object:
            if self.options.get("skip_download") is True:
                subtitle_path = tmp_path / "Video [abc].id.srt"
                subtitle_path.write_text(
                    "1\n00:00:00,000 --> 00:00:01,000\nHalo\n", encoding="utf-8"
                )
                return {
                    "id": "abc",
                    "title": "Video",
                    "_filename": str(tmp_path / "never-downloaded.mp4"),
                    "requested_subtitles": {
                        "id": {
                            "filepath": str(subtitle_path),
                        }
                    },
                }
            media = tmp_path / "actual.mp4"
            media.write_bytes(b"video")
            return {
                "id": "abc",
                "title": "Video",
                "filepath": str(media),
            }

    job = JobSpec(
        job_id="job-with-srt",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory=str(tmp_path),
        quality=QualityPreset.BEST,
        selected_subtitle=SubtitleTrack(
            language_code="id",
            kind=SubtitleKind.MANUAL,
            is_original=True,
        ),
    )
    command = WorkerCommandEnvelope.for_download(job, worker_run_id="run-with-srt")
    output = StringIO()

    rc = run_worker(StringIO(command.to_json_line()), output, ydl_factory=SubtitleYoutubeDL)

    assert rc == 0
    events = _events(output)
    output_paths = [
        str(event.payload["path"])
        for event in events
        if event.event_type is WorkerEventType.OUTPUT_READY
    ]
    assert output_paths == [
        str(tmp_path / "actual.mp4"),
        str(tmp_path / "Video [abc].id.srt"),
    ]
    assert not any(event.event_type is WorkerEventType.WARNING for event in events)
