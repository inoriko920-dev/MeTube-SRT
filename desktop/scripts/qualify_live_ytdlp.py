from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from threading import Event, Thread
from typing import Any

from metube_srt_desktop.adapters.download import (
    SubprocessDownloadWorkerFactory,
    SubprocessSourceResolver,
)
from metube_srt_desktop.application.download_planning import (
    DownloadSelection,
    plan_download_jobs,
)
from metube_srt_desktop.application.dto.download import ResolveRequest, ResolvedSource
from metube_srt_desktop.application.dto.worker_protocol import WorkerEnvelope, WorkerEventType
from metube_srt_desktop.application.ports.download_worker import DownloadWorkerError
from metube_srt_desktop.application.ports.source_resolver import SourceResolveError
from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset, SourceKind
from metube_srt_desktop.domain.subtitles import SubtitleKind

DEFAULT_SINGLE_URL = "https://www.youtube.com/watch?v=BaW_jenozKc"
DEFAULT_PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLt5yu3-wZAlSLRHmI1qNm0wjyVNWw1pCU"
DEFAULT_CHANNEL_URL = "https://www.youtube.com/@coletdjnz/videos"
DEFAULT_CANCEL_URL = "https://www.youtube.com/watch?v=YE7VzlLtp-4"
DEFAULT_FAILURE_URL = "https://www.youtube.com/watch?v=yZIXLfi8CZQ"


class QualificationError(RuntimeError):
    """Live qualification assertion failed."""


def _env_url(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def _timed_resolve(
    resolver: SubprocessSourceResolver,
    url: str,
) -> tuple[ResolvedSource, float]:
    started = time.monotonic()
    source = resolver.resolve(ResolveRequest(url))
    return source, time.monotonic() - started


def _assert_kind(source: ResolvedSource, expected: SourceKind) -> None:
    if source.kind is not expected:
        raise QualificationError(f"expected {expected.value} source, received {source.kind.value}")
    if not source.items:
        raise QualificationError("resolved source did not contain any video items")


def _event_names(events: Iterable[WorkerEnvelope]) -> list[str]:
    return [event.event_type.value for event in events]


def _run_small_video_with_srt(
    source: ResolvedSource,
    output_directory: Path,
) -> dict[str, Any]:
    output_directory.mkdir(parents=True, exist_ok=True)
    job_ids = iter(("live-video-srt",))
    jobs = plan_download_jobs(
        source,
        DownloadSelection(
            output_directory=str(output_directory),
            quality=QualityPreset.P480,
            subtitle_requested=True,
        ),
        job_id_factory=job_ids.__next__,
    )
    if len(jobs) != 1:
        raise QualificationError("single-video qualification did not produce exactly one job")

    job = jobs[0]
    subtitle = job.selected_subtitle
    if subtitle is None:
        raise QualificationError("test video did not expose an eligible original subtitle")
    if subtitle.kind is not SubtitleKind.MANUAL:
        raise QualificationError("test video did not select the expected manual subtitle")
    if subtitle.is_translated:
        raise QualificationError("translated subtitle was selected during live qualification")

    worker = SubprocessDownloadWorkerFactory().create(
        job,
        worker_run_id="live-video-srt-run",
    )
    started = time.monotonic()
    events = tuple(worker.events())
    elapsed = time.monotonic() - started

    if not events or events[-1].event_type is not WorkerEventType.SUCCEEDED:
        raise QualificationError("video+SRT worker did not finish with SUCCEEDED")
    if not any(event.event_type is WorkerEventType.PROGRESS for event in events):
        raise QualificationError("video+SRT worker emitted no live progress event")
    if not any(event.event_type is WorkerEventType.OUTPUT_READY for event in events):
        raise QualificationError("video+SRT worker emitted no output-ready event")

    files = tuple(path for path in output_directory.rglob("*") if path.is_file())
    srt_files = tuple(path for path in files if path.suffix.lower() == ".srt")
    media_files = tuple(
        path for path in files if path.suffix.lower() not in {".srt", ".part", ".ytdl", ".json"}
    )
    if not srt_files:
        raise QualificationError("video+SRT qualification produced no .srt sidecar")
    if not media_files:
        raise QualificationError("video+SRT qualification produced no media file")
    if any(path.stat().st_size <= 0 for path in (*srt_files, *media_files)):
        raise QualificationError("video+SRT qualification produced an empty output file")

    return {
        "elapsed_seconds": round(elapsed, 3),
        "event_types": _event_names(events),
        "subtitle": {
            "language_code": subtitle.language_code,
            "kind": subtitle.kind.value,
            "is_original": subtitle.is_original,
            "is_translated": subtitle.is_translated,
        },
        "srt_files": [path.name for path in srt_files],
        "media_files": [path.name for path in media_files],
    }


def _run_live_cancellation(
    source: ResolvedSource,
    output_directory: Path,
) -> dict[str, Any]:
    output_directory.mkdir(parents=True, exist_ok=True)
    item = source.items[0]
    job = JobSpec(
        job_id="live-cancel",
        source_url=item.webpage_url,
        output_directory=str(output_directory),
        quality=QualityPreset.P480,
        selected_subtitle=None,
    )
    worker = SubprocessDownloadWorkerFactory(
        cancel_grace_seconds=8.0,
        terminate_grace_seconds=3.0,
    ).create(job, worker_run_id="live-cancel-run")

    events: list[WorkerEnvelope] = []
    errors: list[BaseException] = []
    download_phase = Event()
    finished = Event()

    def consume() -> None:
        try:
            for event in worker.events():
                events.append(event)
                if (
                    event.event_type is WorkerEventType.PHASE
                    and event.payload.get("phase") == "downloading"
                ):
                    download_phase.set()
        except BaseException as exc:
            errors.append(exc)
        finally:
            finished.set()

    thread = Thread(target=consume, name="live-cancel-qualification", daemon=True)
    started = time.monotonic()
    thread.start()

    if not download_phase.wait(30.0):
        worker.request_cancel()
        finished.wait(15.0)
        raise QualificationError("live cancel worker never entered downloading phase")

    worker.request_cancel()
    if not finished.wait(30.0):
        raise QualificationError("live cancel worker did not stop after cancellation")
    thread.join(timeout=1.0)

    if errors:
        error = errors[0]
        if isinstance(error, DownloadWorkerError):
            raise QualificationError(
                f"cancel worker boundary failed: {type(error).__name__}"
            ) from error
        raise QualificationError(
            f"unexpected cancellation consumer error: {type(error).__name__}"
        ) from error

    if not events or events[-1].event_type is not WorkerEventType.CANCELLED:
        raise QualificationError("live cancellation did not finish with CANCELLED")

    return {
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "event_types": _event_names(events),
        "cancel_terminal": events[-1].event_type.value,
    }


def _run_expected_failure(
    resolver: SubprocessSourceResolver,
    url: str,
) -> dict[str, str]:
    try:
        resolver.resolve(ResolveRequest(url))
    except SourceResolveError as exc:
        if not exc.error_code.strip() or not exc.message.strip():
            raise QualificationError("failure path returned an empty sanitized error") from exc
        return {
            "error_code": exc.error_code,
            "message": exc.message,
        }
    raise QualificationError("known private/unavailable video unexpectedly resolved")


def _tool_version(command: str) -> str:
    path = shutil.which(command)
    if path is None:
        return "missing"
    return path


def run(output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)

    urls = {
        "single": _env_url("METUBE_LIVE_SINGLE_URL", DEFAULT_SINGLE_URL),
        "playlist": _env_url("METUBE_LIVE_PLAYLIST_URL", DEFAULT_PLAYLIST_URL),
        "channel": _env_url("METUBE_LIVE_CHANNEL_URL", DEFAULT_CHANNEL_URL),
        "cancel": _env_url("METUBE_LIVE_CANCEL_URL", DEFAULT_CANCEL_URL),
        "failure": _env_url("METUBE_LIVE_FAILURE_URL", DEFAULT_FAILURE_URL),
    }

    resolver = SubprocessSourceResolver(terminate_grace_seconds=3.0)

    single, single_elapsed = _timed_resolve(resolver, urls["single"])
    _assert_kind(single, SourceKind.VIDEO)

    playlist, playlist_elapsed = _timed_resolve(resolver, urls["playlist"])
    _assert_kind(playlist, SourceKind.PLAYLIST)

    channel, channel_elapsed = _timed_resolve(resolver, urls["channel"])
    _assert_kind(channel, SourceKind.CHANNEL)

    cancel_source, cancel_resolve_elapsed = _timed_resolve(resolver, urls["cancel"])
    _assert_kind(cancel_source, SourceKind.VIDEO)

    download_result = _run_small_video_with_srt(single, output_root / "video-srt")
    cancellation_result = _run_live_cancellation(
        cancel_source,
        output_root / "cancel",
    )
    failure_result = _run_expected_failure(resolver, urls["failure"])

    return {
        "schema_version": 1,
        "python": sys.version.split()[0],
        "tools": {
            "ffmpeg": _tool_version("ffmpeg"),
            "ffprobe": _tool_version("ffprobe"),
            "deno": _tool_version("deno"),
        },
        "resolve": {
            "single": {
                "kind": single.kind.value,
                "title": single.title,
                "item_count": len(single.items),
                "elapsed_seconds": round(single_elapsed, 3),
            },
            "playlist": {
                "kind": playlist.kind.value,
                "title": playlist.title,
                "item_count": len(playlist.items),
                "elapsed_seconds": round(playlist_elapsed, 3),
            },
            "channel": {
                "kind": channel.kind.value,
                "title": channel.title,
                "item_count": len(channel.items),
                "elapsed_seconds": round(channel_elapsed, 3),
            },
            "cancel_source": {
                "kind": cancel_source.kind.value,
                "title": cancel_source.title,
                "item_count": len(cancel_source.items),
                "elapsed_seconds": round(cancel_resolve_elapsed, 3),
            },
        },
        "video_srt": download_result,
        "cancellation": cancellation_result,
        "expected_failure": failure_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("build/live-qualification"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("build/live-qualification/report.json"),
    )
    args = parser.parse_args()

    report = run(args.output_root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
