from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot

from metube_srt_desktop.application.download_planning import DownloadSelection
from metube_srt_desktop.application.download_submission import (
    DownloadSubmissionResult,
    EnqueueResolvedSourceUseCase,
    ResolvePlanEnqueueUseCase,
)
from metube_srt_desktop.application.dto.download import ResolvedSource, ResolveRequest
from metube_srt_desktop.application.dto.job_runtime import JobRuntimeSnapshot
from metube_srt_desktop.application.ports.download_queue import QueueRuntimePort
from metube_srt_desktop.application.ports.queue_storage import QueueStorageError
from metube_srt_desktop.application.ports.source_resolver import (
    SourceResolveCancellationPort,
    SourceResolveError,
    SourceResolverPort,
)
from metube_srt_desktop.domain.jobs import JobSpec, JobState, QualityPreset
from metube_srt_desktop.domain.subtitles import SubtitleKind
from metube_srt_desktop.presentation.pages.download.page import DownloadPage
from metube_srt_desktop.presentation.pages.queue.page import QueuePage

_QUALITY_BY_INDEX = {
    0: QualityPreset.BEST,
    1: QualityPreset.P1080,
    2: QualityPreset.P720,
    3: QualityPreset.P480,
}

_ACTIVE_STATES = {
    JobState.RESOLVING,
    JobState.RUNNING,
    JobState.POSTPROCESSING,
    JobState.CANCELLING,
}
_FAILURE_STATES = {JobState.FAILED, JobState.INTERRUPTED}


@dataclass(frozen=True, slots=True)
class _AsyncResult:
    value: object | None
    error: Exception | None


class _TaskSignals(QObject):
    finished = Signal(object, object)


class _ApplicationTask(QRunnable):
    def __init__(self, call: Callable[[], object]) -> None:
        super().__init__()
        self._call = call
        self.signals = _TaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = _AsyncResult(self._call(), None)
        except Exception as exc:  # presentation boundary must not display raw exceptions
            result = _AsyncResult(None, exc)
        self.signals.finished.emit(self, result)


class DownloadQueueController(QObject):
    """Bind frozen Download/Queue views to application-owned use cases."""

    def __init__(
        self,
        download_page: DownloadPage,
        queue_page: QueuePage,
        resolver: SourceResolverPort,
        queue: QueueRuntimePort,
        *,
        parent: QObject | None = None,
        thread_pool: QThreadPool | None = None,
    ) -> None:
        super().__init__(parent)
        self._download_page = download_page
        self._queue_page = queue_page
        self._resolver = resolver
        self._queue = queue
        self._enqueue_resolved = EnqueueResolvedSourceUseCase(queue)
        self._resolve_and_enqueue = ResolvePlanEnqueueUseCase(resolver, queue)
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._resolved_source: ResolvedSource | None = None
        self._resolved_url: str | None = None
        self._title_by_job_id: dict[str, str] = {}
        self._busy = False
        self._closed = False
        self._tasks: set[_ApplicationTask] = set()
        self._task_handlers: dict[_ApplicationTask, Callable[[_AsyncResult], None]] = {}

        self._download_page.resolve_button.clicked.connect(self.resolve_current_url)
        self._download_page.enqueue_button.clicked.connect(self.enqueue_current_url)
        self._queue_page.cancel_requested.connect(self.cancel_job)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(120)
        self._poll_timer.timeout.connect(self.refresh_queue)
        self._poll_timer.start()
        self.refresh_queue()

    @Slot()
    def resolve_current_url(self) -> None:
        if self._closed or self._busy:
            return

        raw_url = self._download_page.url_input.text().strip()
        try:
            request = ResolveRequest(raw_url)
        except ValueError as exc:
            self._download_page.show_error(_safe_validation_message(exc))
            return

        self._set_busy(True)
        self._download_page.show_resolving()
        self._start_task(
            lambda: self._resolver.resolve(request),
            self._handle_resolve_result,
        )

    @Slot()
    def enqueue_current_url(self) -> None:
        if self._closed or self._busy:
            return

        raw_url = self._download_page.url_input.text().strip()
        try:
            request = ResolveRequest(raw_url)
            selection = self._current_selection()
        except ValueError as exc:
            self._download_page.show_error(_safe_validation_message(exc))
            return

        self._set_busy(True)
        self._download_page.show_enqueuing()

        cached = self._resolved_source
        if cached is not None and self._resolved_url == raw_url:
            self._start_task(
                lambda: self._enqueue_resolved.execute(cached, selection),
                self._handle_submission_result,
            )
            return

        self._start_task(
            lambda: self._resolve_and_enqueue.execute(request, selection),
            self._handle_submission_result,
        )

    @Slot(str)
    def cancel_job(self, job_id: str) -> None:
        try:
            self._queue.cancel(job_id)
        except (KeyError, QueueStorageError):
            return
        self.refresh_queue()

    @Slot()
    def refresh_queue(self) -> None:
        if self._closed:
            return
        self._queue.drain_updates()
        snapshots = self._queue.snapshots()
        specs = {job.job_id: job for job in self._queue.job_specs()}

        for snapshot in snapshots:
            spec = specs.get(snapshot.job_id)
            self._queue_page.upsert_job(
                job_id=snapshot.job_id,
                title=self._display_title(snapshot.job_id, spec),
                kind="Video",
                status=_status_label(snapshot),
                progress=_progress_label(snapshot),
                srt=_subtitle_label(spec),
            )

        self._queue_page.set_counts(
            active=sum(snapshot.state in _ACTIVE_STATES for snapshot in snapshots),
            waiting=sum(snapshot.state is JobState.QUEUED for snapshot in snapshots),
            failed=sum(snapshot.state in _FAILURE_STATES for snapshot in snapshots),
        )

    def _start_task(
        self,
        call: Callable[[], object],
        handler: Callable[[_AsyncResult], None],
    ) -> None:
        if self._closed:
            return
        task = _ApplicationTask(call)
        task.signals.finished.connect(self._task_finished)
        self._task_handlers[task] = handler
        self._tasks.add(task)
        self._thread_pool.start(task)

    @Slot(object, object)
    def _task_finished(self, raw_task: object, raw_result: object) -> None:
        task = cast(_ApplicationTask, raw_task)
        handler = self._task_handlers.pop(task, None)
        self._tasks.discard(task)
        if self._closed or handler is None:
            return
        handler(cast(_AsyncResult, raw_result))

    def _handle_resolve_result(self, result: _AsyncResult) -> None:
        self._set_busy(False)
        if result.error is not None:
            self._resolved_source = None
            self._resolved_url = None
            self._download_page.show_error(_resolve_error_message(result.error))
            return

        source = cast(ResolvedSource, result.value)
        self._resolved_source = source
        self._resolved_url = self._download_page.url_input.text().strip()
        self._download_page.show_resolved(
            source.title,
            item_count=len(source.items),
        )

    def _handle_submission_result(self, result: _AsyncResult) -> None:
        self._set_busy(False)
        if result.error is not None:
            self._download_page.show_error(_submission_error_message(result.error))
            return

        submission = cast(DownloadSubmissionResult, result.value)
        self._resolved_source = submission.source
        self._resolved_url = self._download_page.url_input.text().strip()
        self._remember_titles(submission)
        self._download_page.show_queued(len(submission.jobs))
        self.refresh_queue()

    def _remember_titles(self, submission: DownloadSubmissionResult) -> None:
        for job, item in zip(submission.jobs, submission.source.items, strict=True):
            self._title_by_job_id[job.job_id] = item.title

    def _current_selection(self) -> DownloadSelection:
        quality = _QUALITY_BY_INDEX.get(self._download_page.quality_combo.currentIndex())
        if quality is None:
            raise ValueError("invalid quality selection")
        raw_output = self._download_page.output_path.text().strip()
        if not raw_output:
            raise ValueError("output_directory must be non-empty")
        output_directory = str(Path(raw_output).expanduser().resolve(strict=False))
        return DownloadSelection(
            output_directory=output_directory,
            quality=quality,
            subtitle_requested=self._download_page.subtitle_checkbox.isChecked(),
        )

    def _display_title(self, job_id: str, spec: JobSpec | None) -> str:
        title = self._title_by_job_id.get(job_id)
        if title is not None:
            return title
        if spec is not None:
            return spec.display_title or spec.source_url
        return job_id

    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._task_handlers.clear()
        self._poll_timer.stop()
        if isinstance(self._resolver, SourceResolveCancellationPort):
            self._resolver.cancel_current()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._download_page.set_busy(busy)


def _status_label(snapshot: JobRuntimeSnapshot) -> str:
    label = {
        JobState.QUEUED: "Menunggu",
        JobState.RESOLVING: "Memeriksa",
        JobState.RUNNING: "Mengunduh",
        JobState.POSTPROCESSING: "Memproses",
        JobState.CANCELLING: "Membatalkan",
        JobState.SUCCEEDED: "Selesai",
        JobState.FAILED: "Gagal",
        JobState.CANCELLED: "Dibatalkan",
        JobState.INTERRUPTED: "Terputus",
    }[snapshot.state]

    if snapshot.state in {JobState.FAILED, JobState.INTERRUPTED}:
        detail = snapshot.error_message or snapshot.error_code
        if detail:
            return f"{label}: {detail}"
    return label


def _progress_label(snapshot: JobRuntimeSnapshot) -> str:
    if snapshot.state is JobState.SUCCEEDED:
        return "100%"
    if snapshot.progress_percent is None:
        return "0%"
    return f"{snapshot.progress_percent:.0f}%"


def _subtitle_label(spec: JobSpec | None) -> str:
    if spec is None or spec.selected_subtitle is None:
        return "Tidak ada"
    if spec.selected_subtitle.kind is SubtitleKind.MANUAL:
        return "Manual"
    return "Auto asli"


def _safe_validation_message(error: ValueError) -> str:
    message = str(error).strip()
    if "output_directory" in message:
        return "Pilih folder tujuan download."
    if "source_url must be non-empty" in message:
        return "Masukkan URL YouTube terlebih dahulu."
    if "YouTube URL" in message or "absolute http" in message or "embedded credentials" in message:
        return "Masukkan URL YouTube yang valid."
    return "Periksa kembali URL dan opsi download."


def _resolve_error_message(error: Exception) -> str:
    if isinstance(error, SourceResolveError):
        return error.message
    return "URL tidak dapat diperiksa saat ini."


def _submission_error_message(error: Exception) -> str:
    if isinstance(error, SourceResolveError):
        return error.message
    if isinstance(error, QueueStorageError):
        return "Penyimpanan antrian tidak tersedia."
    return "Pekerjaan tidak dapat ditambahkan ke antrian."
