from __future__ import annotations

from collections.abc import Iterable, Mapping

from metube_srt_desktop.application.dto.worker_protocol import (
    WORKER_PROTOCOL_VERSION,
    WorkerEnvelope,
    WorkerEventType,
)
from metube_srt_desktop.application.job_lifecycle import DownloadJobRun
from metube_srt_desktop.application.ports.download_worker import DownloadWorkerError
from metube_srt_desktop.domain.jobs import JobSpec, JobState, QualityPreset


class FakeWorker:
    def __init__(
        self,
        events: Iterable[WorkerEnvelope] = (),
        *,
        fail_events: bool = False,
        fail_cancel: bool = False,
    ) -> None:
        self._events = tuple(events)
        self._fail_events = fail_events
        self._fail_cancel = fail_cancel
        self.cancel_requests = 0

    def events(self) -> Iterable[WorkerEnvelope]:
        if self._fail_events:
            raise DownloadWorkerError("worker boundary failed")
        yield from self._events

    def request_cancel(self) -> None:
        self.cancel_requests += 1
        if self._fail_cancel:
            raise DownloadWorkerError("cancel boundary failed")


def make_job() -> JobSpec:
    return JobSpec(
        job_id="job-1",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory="Downloads",
        quality=QualityPreset.P1080,
        selected_subtitle=None,
    )


def event(
    event_type: WorkerEventType,
    sequence: int,
    payload: Mapping[str, object] | None = None,
    *,
    job_id: str = "job-1",
    worker_run_id: str = "run-1",
) -> WorkerEnvelope:
    return WorkerEnvelope(
        schema_version=WORKER_PROTOCOL_VERSION,
        event_type=event_type,
        job_id=job_id,
        worker_run_id=worker_run_id,
        sequence=sequence,
        payload={} if payload is None else payload,
    )


def test_download_lifecycle_maps_worker_events_to_canonical_snapshot() -> None:
    worker = FakeWorker(
        (
            event(WorkerEventType.READY, 0),
            event(
                WorkerEventType.PROGRESS,
                1,
                {
                    "phase": "download",
                    "percent": 50.0,
                    "downloaded_bytes": 500,
                    "total_bytes": 1000,
                    "speed_bytes_per_second": 250.5,
                    "eta_seconds": 2,
                },
            ),
            event(WorkerEventType.PHASE, 2, {"phase": "postprocessing"}),
            event(WorkerEventType.OUTPUT_READY, 3, {"path": "Downloads/video.mp4"}),
            event(WorkerEventType.SUCCEEDED, 4, {"mode": "download"}),
        )
    )
    run = DownloadJobRun(make_job(), worker_run_id="run-1", worker=worker)

    updates = list(run.updates())

    assert [update.state for update in updates] == [
        JobState.RUNNING,
        JobState.RUNNING,
        JobState.POSTPROCESSING,
        JobState.POSTPROCESSING,
        JobState.SUCCEEDED,
    ]
    final = updates[-1]
    assert final.progress_percent == 50.0
    assert final.downloaded_bytes == 500
    assert final.total_bytes == 1000
    assert final.speed_bytes_per_second == 250.5
    assert final.eta_seconds == 2.0
    assert final.output_paths == ("Downloads/video.mp4",)
    assert final.last_sequence == 4


def test_stale_worker_run_event_cannot_mutate_application_state() -> None:
    worker = FakeWorker(
        (
            event(
                WorkerEventType.FAILED,
                99,
                {"error_code": "stale", "message": "old"},
                worker_run_id="old-run",
            ),
            event(WorkerEventType.READY, 0),
            event(WorkerEventType.SUCCEEDED, 1),
        )
    )
    run = DownloadJobRun(make_job(), worker_run_id="run-1", worker=worker)

    updates = list(run.updates())

    assert [update.state for update in updates] == [JobState.RUNNING, JobState.SUCCEEDED]
    assert updates[-1].error_code is None


def test_worker_failure_payload_becomes_failed_job_state() -> None:
    worker = FakeWorker(
        (
            event(WorkerEventType.READY, 0),
            event(
                WorkerEventType.FAILED,
                1,
                {"error_code": "yt_dlp_error", "message": "yt-dlp operation failed"},
            ),
        )
    )
    run = DownloadJobRun(make_job(), worker_run_id="run-1", worker=worker)

    final = list(run.updates())[-1]

    assert final.state is JobState.FAILED
    assert final.error_code == "yt_dlp_error"
    assert final.error_message == "yt-dlp operation failed"


def test_worker_boundary_failure_becomes_interrupted_not_failed() -> None:
    run = DownloadJobRun(
        make_job(),
        worker_run_id="run-1",
        worker=FakeWorker(fail_events=True),
    )

    final = list(run.updates())[-1]

    assert final.state is JobState.INTERRUPTED
    assert final.error_code == "worker_process_failed"
    assert final.error_message == "worker boundary failed"


def test_worker_stream_ending_without_terminal_event_becomes_interrupted() -> None:
    run = DownloadJobRun(
        make_job(),
        worker_run_id="run-1",
        worker=FakeWorker((event(WorkerEventType.READY, 0),)),
    )

    final = list(run.updates())[-1]

    assert final.state is JobState.INTERRUPTED
    assert final.error_code == "worker_stream_ended"
    assert final.error_message == "Download worker stream ended before a terminal event"


def test_cancel_sets_cancelling_then_accepts_cancelled_terminal_event() -> None:
    worker = FakeWorker(
        (
            event(WorkerEventType.READY, 0),
            event(WorkerEventType.CANCELLED, 1, {"reason": "requested"}),
        )
    )
    run = DownloadJobRun(make_job(), worker_run_id="run-1", worker=worker)

    cancelling = run.cancel()
    updates = list(run.updates())

    assert cancelling.state is JobState.CANCELLING
    assert worker.cancel_requests == 1
    assert updates[0].state is JobState.CANCELLING
    assert updates[-1].state is JobState.CANCELLED


def test_cancel_boundary_failure_becomes_interrupted() -> None:
    worker = FakeWorker(fail_cancel=True)
    run = DownloadJobRun(make_job(), worker_run_id="run-1", worker=worker)

    snapshot = run.cancel()

    assert snapshot.state is JobState.INTERRUPTED
    assert snapshot.error_code == "worker_cancel_failed"
    assert snapshot.error_message == "cancel boundary failed"


def test_updates_are_single_consumer() -> None:
    run = DownloadJobRun(
        make_job(),
        worker_run_id="run-1",
        worker=FakeWorker(
            (
                event(WorkerEventType.READY, 0),
                event(WorkerEventType.SUCCEEDED, 1),
            )
        ),
    )

    list(run.updates())

    try:
        list(run.updates())
    except RuntimeError as exc:
        assert "only be consumed once" in str(exc)
    else:
        raise AssertionError("second updates() consumption should fail")


def test_worker_stop_after_successful_cancel_request_is_cancelled() -> None:
    worker = FakeWorker(fail_events=True)
    run = DownloadJobRun(make_job(), worker_run_id="run-1", worker=worker)

    cancelling = run.cancel()
    final = list(run.updates())[-1]

    assert cancelling.state is JobState.CANCELLING
    assert worker.cancel_requests == 1
    assert final.state is JobState.CANCELLED
    assert final.error_code is None
    assert final.warning_message == "Worker dihentikan paksa setelah permintaan pembatalan"



class TailFailWorker:
    def events(self) -> Iterable[WorkerEnvelope]:
        yield event(WorkerEventType.READY, 0)
        yield event(WorkerEventType.SUCCEEDED, 1)
        raise DownloadWorkerError("worker exited after success event")

    def request_cancel(self) -> None:
        return


def test_success_is_not_committed_until_worker_boundary_exits_cleanly() -> None:
    run = DownloadJobRun(
        make_job(),
        worker_run_id="run-1",
        worker=TailFailWorker(),
    )

    updates = list(run.updates())

    assert [item.state for item in updates] == [
        JobState.RUNNING,
        JobState.INTERRUPTED,
    ]
    assert updates[-1].error_code == "worker_process_failed"
    assert updates[-1].error_message == "worker exited after success event"
