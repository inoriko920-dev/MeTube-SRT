import pytest

from metube_srt_desktop.worker.protocol import (
    WORKER_PROTOCOL_VERSION,
    WorkerEnvelope,
    WorkerEventType,
)


def test_worker_envelope_round_trip() -> None:
    event = WorkerEnvelope(
        schema_version=WORKER_PROTOCOL_VERSION,
        event_type=WorkerEventType.PROGRESS,
        job_id="job-1",
        worker_run_id="run-1",
        sequence=3,
        payload={"percent": 42.5, "phase": "download"},
    )

    decoded = WorkerEnvelope.from_json_line(event.to_json_line())

    assert decoded == event


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("job_id", ""),
        ("worker_run_id", " "),
        ("sequence", -1),
    ],
)
def test_worker_envelope_rejects_invalid_identity(field: str, value: object) -> None:
    kwargs: dict[str, object] = {
        "schema_version": WORKER_PROTOCOL_VERSION,
        "event_type": WorkerEventType.READY,
        "job_id": "job-1",
        "worker_run_id": "run-1",
        "sequence": 0,
        "payload": {},
    }
    kwargs[field] = value

    with pytest.raises(ValueError):
        WorkerEnvelope(**kwargs)  # type: ignore[arg-type]


def test_worker_envelope_rejects_unknown_protocol_version() -> None:
    with pytest.raises(ValueError, match="unsupported worker protocol version"):
        WorkerEnvelope(
            schema_version=999,
            event_type=WorkerEventType.READY,
            job_id="job-1",
            worker_run_id="run-1",
            sequence=0,
            payload={},
        )
