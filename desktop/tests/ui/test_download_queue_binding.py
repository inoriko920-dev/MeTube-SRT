from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from threading import Event

from pytestqt.qtbot import QtBot

from metube_srt_desktop.application.download_queue import BoundedDownloadQueue
from metube_srt_desktop.application.dto.download import (
    ResolvedItem,
    ResolvedSource,
    ResolveRequest,
)
from metube_srt_desktop.application.dto.worker_protocol import (
    WORKER_PROTOCOL_VERSION,
    WorkerEnvelope,
    WorkerEventType,
)
from metube_srt_desktop.application.ports.download_worker import DownloadWorkerPort
from metube_srt_desktop.domain.jobs import JobSpec, JobState, SourceKind
from metube_srt_desktop.domain.subtitles import SubtitleKind, SubtitleTrack
from metube_srt_desktop.presentation.shell.main_window import MainWindow, PageId


class FakeResolver:
    def __init__(self) -> None:
        self.requests: list[ResolveRequest] = []
        self.source = ResolvedSource(
            source_url="https://www.youtube.com/watch?v=abc",
            kind=SourceKind.VIDEO,
            title="Video Uji",
            items=(
                ResolvedItem(
                    video_id="abc",
                    title="Video Uji",
                    webpage_url="https://www.youtube.com/watch?v=abc",
                    subtitles=(
                        SubtitleTrack(
                            language_code="id",
                            kind=SubtitleKind.MANUAL,
                            is_original=True,
                        ),
                    ),
                ),
            ),
        )

    def resolve(self, request: ResolveRequest) -> ResolvedSource:
        self.requests.append(request)
        return self.source


class ImmediateWorker:
    def __init__(self, job_id: str, worker_run_id: str) -> None:
        self.job_id = job_id
        self.worker_run_id = worker_run_id

    def events(self) -> Iterable[WorkerEnvelope]:
        yield _event(self.job_id, self.worker_run_id, WorkerEventType.READY, 0)
        yield _event(self.job_id, self.worker_run_id, WorkerEventType.SUCCEEDED, 1)

    def request_cancel(self) -> None:
        return


class ImmediateWorkerFactory:
    def create(
        self,
        job: JobSpec,
        *,
        worker_run_id: str,
    ) -> DownloadWorkerPort:
        return ImmediateWorker(job.job_id, worker_run_id)


class HoldingWorker:
    def __init__(self, job_id: str, worker_run_id: str) -> None:
        self.job_id = job_id
        self.worker_run_id = worker_run_id
        self.started = Event()
        self.release = Event()
        self.cancelled = Event()

    def events(self) -> Iterable[WorkerEnvelope]:
        self.started.set()
        yield _event(self.job_id, self.worker_run_id, WorkerEventType.READY, 0)
        self.release.wait(2.0)
        terminal = (
            WorkerEventType.CANCELLED if self.cancelled.is_set() else WorkerEventType.SUCCEEDED
        )
        yield _event(self.job_id, self.worker_run_id, terminal, 1)

    def request_cancel(self) -> None:
        self.cancelled.set()
        self.release.set()


class HoldingWorkerFactory:
    def __init__(self) -> None:
        self.worker: HoldingWorker | None = None

    def create(
        self,
        job: JobSpec,
        *,
        worker_run_id: str,
    ) -> DownloadWorkerPort:
        self.worker = HoldingWorker(job.job_id, worker_run_id)
        return self.worker


def _event(
    job_id: str,
    worker_run_id: str,
    event_type: WorkerEventType,
    sequence: int,
) -> WorkerEnvelope:
    return WorkerEnvelope(
        schema_version=WORKER_PROTOCOL_VERSION,
        event_type=event_type,
        job_id=job_id,
        worker_run_id=worker_run_id,
        sequence=sequence,
        payload={},
    )


def test_resolve_button_previews_without_enqueuing(qtbot: QtBot) -> None:
    resolver = FakeResolver()
    queue = BoundedDownloadQueue(ImmediateWorkerFactory())
    window = MainWindow(resolver=resolver, queue=queue)
    qtbot.addWidget(window)
    window.show()

    try:
        window.download_page.url_input.setText(resolver.source.source_url)
        window.download_page.resolve_button.click()

        qtbot.waitUntil(
            lambda: window.download_page.state_title.text() == "Siap ditambahkan ke antrian",
            timeout=2000,
        )

        assert resolver.requests == [ResolveRequest(resolver.source.source_url)]
        assert queue.snapshots() == ()
        assert "1 video ditemukan" in window.download_page.state_text.text()
    finally:
        queue.shutdown(wait=True)


def test_enqueue_button_updates_real_queue_table(qtbot: QtBot) -> None:
    resolver = FakeResolver()
    queue = BoundedDownloadQueue(ImmediateWorkerFactory())
    window = MainWindow(resolver=resolver, queue=queue)
    qtbot.addWidget(window)
    window.show()

    try:
        window.download_page.url_input.setText(resolver.source.source_url)
        window.download_page.enqueue_button.click()

        qtbot.waitUntil(
            lambda: len(queue.snapshots()) == 1
            and queue.snapshots()[0].state is JobState.SUCCEEDED,
            timeout=2000,
        )
        qtbot.waitUntil(lambda: window.queue_page.model.rowCount() == 1, timeout=2000)

        assert window.queue_page.model.item(0, 0).text() == "Video Uji"
        assert window.queue_page.model.item(0, 1).text() == "Video"
        assert window.queue_page.model.item(0, 2).text() == "Selesai"
        assert window.queue_page.model.item(0, 3).text() == "100%"
        assert window.queue_page.model.item(0, 4).text() == "Manual"
        assert window.download_page.state_title.text() == "Ditambahkan ke antrian"
    finally:
        queue.shutdown(wait=True)


def test_queue_cancel_action_routes_to_application_queue(qtbot: QtBot) -> None:
    resolver = FakeResolver()
    factory = HoldingWorkerFactory()
    queue = BoundedDownloadQueue(factory, concurrency=1)
    window = MainWindow(resolver=resolver, queue=queue)
    qtbot.addWidget(window)
    window.show()

    try:
        window.download_page.url_input.setText(resolver.source.source_url)
        window.download_page.enqueue_button.click()

        qtbot.waitUntil(lambda: factory.worker is not None, timeout=2000)
        worker = factory.worker
        assert worker is not None
        assert worker.started.wait(1.0)

        qtbot.waitUntil(lambda: window.queue_page.model.rowCount() == 1, timeout=2000)
        window.navigate(PageId.QUEUE.value)
        window.queue_page.table.selectRow(0)
        window.queue_page.request_cancel_selected()

        qtbot.waitUntil(
            lambda: queue.snapshots()[0].state is JobState.CANCELLED,
            timeout=2000,
        )
        qtbot.waitUntil(
            lambda: window.queue_page.model.item(0, 2).text() == "Dibatalkan",
            timeout=2000,
        )

        assert worker.cancelled.is_set()
    finally:
        queue.shutdown(wait=True)
