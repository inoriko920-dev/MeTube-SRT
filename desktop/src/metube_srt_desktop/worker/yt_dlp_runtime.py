from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from threading import Event
from time import monotonic
from types import TracebackType
from typing import Protocol, cast

from metube_srt_desktop.application.dto.download import ResolvedSource, ResolveRequest
from metube_srt_desktop.application.dto.worker_protocol import WorkerEventType
from metube_srt_desktop.domain.jobs import JobSpec
from metube_srt_desktop.worker.yt_dlp_options import (
    build_download_options,
    build_resolve_options,
    build_subtitle_only_options,
)
from metube_srt_desktop.worker.yt_dlp_resolver import is_collection_url, map_resolved_source

WorkerEmit = Callable[[WorkerEventType, Mapping[str, object]], None]

_PROGRESS_EMIT_INTERVAL_SECONDS = 0.15


class YoutubeDLSession(Protocol):
    def __enter__(self) -> YoutubeDLSession: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> object: ...

    def extract_info(self, url: str, *, download: bool) -> object: ...


YoutubeDLFactory = Callable[[dict[str, object]], YoutubeDLSession]


class DownloadCancellationRequested(RuntimeError):
    """Internal control-flow exception raised only from yt-dlp hooks."""


def _default_ydl_factory(options: dict[str, object]) -> YoutubeDLSession:
    from yt_dlp import YoutubeDL

    factory = cast(YoutubeDLFactory, YoutubeDL)
    return factory(options)


def resolve_source_live(
    request: ResolveRequest,
    *,
    ydl_factory: YoutubeDLFactory | None = None,
) -> ResolvedSource:
    """Run metadata extraction through yt-dlp without downloading media."""

    factory = ydl_factory or _default_ydl_factory
    collection = is_collection_url(request.source_url)
    with factory(
        build_resolve_options(
            tolerate_unavailable_entries=collection,
            force_single_video=not collection,
        )
    ) as ydl:
        raw_info = ydl.extract_info(request.source_url, download=False)

    if not isinstance(raw_info, Mapping):
        raise ValueError("yt-dlp resolve result must be an object")
    return map_resolved_source(request, cast(Mapping[str, object], raw_info))


def download_job_live(
    job: JobSpec,
    *,
    cancellation: Event,
    emit: WorkerEmit,
    ydl_factory: YoutubeDLFactory | None = None,
) -> tuple[str, ...]:
    """Execute one immutable single-video job and emit sanitized runtime events."""

    if cancellation.is_set():
        raise DownloadCancellationRequested

    media_job = replace(job, selected_subtitle=None)
    options = build_download_options(media_job)
    options["progress_hooks"] = [_progress_hook(cancellation, emit)]
    options["postprocessor_hooks"] = [_postprocessor_hook(cancellation, emit)]

    factory = ydl_factory or _default_ydl_factory
    with factory(options) as ydl:
        raw_info = ydl.extract_info(job.source_url, download=True)

    if cancellation.is_set():
        raise DownloadCancellationRequested
    if not isinstance(raw_info, Mapping):
        raise ValueError("yt-dlp download result must be an object")

    outputs = list(
        _collect_output_paths(
            cast(Mapping[str, object], raw_info),
            output_directory=job.output_directory,
        )
    )

    if job.selected_subtitle is not None:
        subtitle_outputs = _download_selected_subtitle(
            job,
            cancellation=cancellation,
            emit=emit,
            factory=factory,
        )
        for output_path in subtitle_outputs:
            if output_path not in outputs:
                outputs.append(output_path)

    return tuple(outputs)


def _progress_hook(
    cancellation: Event,
    emit: WorkerEmit,
) -> Callable[[Mapping[str, object]], None]:
    last_emit_at: float | None = None

    def hook(status: Mapping[str, object]) -> None:
        nonlocal last_emit_at

        if cancellation.is_set():
            raise DownloadCancellationRequested

        state = status.get("status")
        if state == "downloading":
            now = monotonic()
            if last_emit_at is not None and now - last_emit_at < _PROGRESS_EMIT_INTERVAL_SECONDS:
                return
            last_emit_at = now

            payload: dict[str, object] = {"phase": "download"}
            downloaded = _numeric(status.get("downloaded_bytes"))
            total = _numeric(status.get("total_bytes"))
            if total is None:
                total = _numeric(status.get("total_bytes_estimate"))
            speed = _numeric(status.get("speed"))
            eta = _numeric(status.get("eta"))

            if downloaded is not None:
                payload["downloaded_bytes"] = downloaded
            if total is not None:
                payload["total_bytes"] = total
            if downloaded is not None and total is not None and total > 0:
                payload["percent"] = max(0.0, min(100.0, downloaded * 100.0 / total))
            if speed is not None:
                payload["speed_bytes_per_second"] = speed
            if eta is not None:
                payload["eta_seconds"] = eta
            emit(WorkerEventType.PROGRESS, payload)
        elif state == "finished":
            payload: dict[str, object] = {
                "phase": "download",
                "percent": 100.0,
            }
            downloaded = _numeric(status.get("downloaded_bytes"))
            total = _numeric(status.get("total_bytes"))
            if downloaded is not None:
                payload["downloaded_bytes"] = downloaded
            if total is not None:
                payload["total_bytes"] = total
            emit(WorkerEventType.PROGRESS, payload)
            emit(WorkerEventType.PHASE, {"phase": "postprocessing"})

    return hook


def _postprocessor_hook(
    cancellation: Event,
    emit: WorkerEmit,
) -> Callable[[Mapping[str, object]], None]:
    def hook(status: Mapping[str, object]) -> None:
        if cancellation.is_set():
            raise DownloadCancellationRequested
        if status.get("status") in {"started", "processing"}:
            emit(WorkerEventType.PHASE, {"phase": "postprocessing"})

    return hook


def _numeric(value: object) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _collect_output_paths(
    raw_info: Mapping[str, object],
    *,
    output_directory: str,
) -> tuple[str, ...]:
    candidates: list[str] = []
    _append_path_candidate(candidates, raw_info.get("filepath"))
    _append_path_candidate(candidates, raw_info.get("_filename"))

    requested_downloads = raw_info.get("requested_downloads")
    if isinstance(requested_downloads, Sequence) and not isinstance(
        requested_downloads, (str, bytes, bytearray)
    ):
        for entry in cast(Sequence[object], requested_downloads):
            if isinstance(entry, Mapping):
                mapping = cast(Mapping[str, object], entry)
                _append_path_candidate(candidates, mapping.get("filepath"))
                _append_path_candidate(candidates, mapping.get("filename"))

    requested_subtitles = raw_info.get("requested_subtitles")
    if isinstance(requested_subtitles, Mapping):
        subtitle_map = cast(Mapping[object, object], requested_subtitles)
        for value in subtitle_map.values():
            if isinstance(value, Mapping):
                mapping = cast(Mapping[str, object], value)
                _append_path_candidate(candidates, mapping.get("filepath"))
                _append_path_candidate(candidates, mapping.get("filename"))

    safe_paths: list[str] = []
    for candidate in candidates:
        safe = _safe_output_path(output_directory, candidate)
        if safe is not None and safe not in safe_paths:
            safe_paths.append(safe)
    return tuple(safe_paths)


def _append_path_candidate(target: list[str], value: object) -> None:
    if isinstance(value, str) and value.strip():
        target.append(value)


def _safe_output_path(output_directory: str, candidate: str) -> str | None:
    base = Path(output_directory).expanduser().resolve(strict=False)
    path = Path(candidate).expanduser()
    if path.is_absolute():
        resolved = path.resolve(strict=False)
    else:
        from_cwd = path.resolve(strict=False)
        try:
            from_cwd.relative_to(base)
        except ValueError:
            resolved = (base / path).resolve(strict=False)
        else:
            resolved = from_cwd
    try:
        resolved.relative_to(base)
    except ValueError:
        return None
    return str(resolved)


def _download_selected_subtitle(
    job: JobSpec,
    *,
    cancellation: Event,
    emit: WorkerEmit,
    factory: YoutubeDLFactory,
) -> tuple[str, ...]:
    if cancellation.is_set():
        raise DownloadCancellationRequested

    emit(WorkerEventType.PHASE, {"phase": "postprocessing"})
    options = build_subtitle_only_options(job)
    options["postprocessor_hooks"] = [_postprocessor_hook(cancellation, emit)]

    try:
        with factory(options) as ydl:
            raw_info = ydl.extract_info(job.source_url, download=True)
        if cancellation.is_set():
            raise DownloadCancellationRequested
        if not isinstance(raw_info, Mapping):
            raise ValueError("yt-dlp subtitle result must be an object")
        return _collect_output_paths(
            cast(Mapping[str, object], raw_info),
            output_directory=job.output_directory,
        )
    except DownloadCancellationRequested:
        raise
    except Exception:
        emit(
            WorkerEventType.WARNING,
            {"message": ("Subtitle tidak berhasil diambil; video tetap disimpan tanpa subtitle")},
        )
        return ()
