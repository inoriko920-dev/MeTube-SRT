from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

WORKER_PROTOCOL_VERSION: Final[int] = 1


class WorkerEventType(StrEnum):
    READY = "ready"
    PHASE = "phase"
    PROGRESS = "progress"
    WARNING = "warning"
    OUTPUT_READY = "output_ready"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


def _require_str(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _require_int(raw: Mapping[str, object], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{key} must be an integer")
    return value


@dataclass(frozen=True, slots=True)
class WorkerEnvelope:
    schema_version: int
    event_type: WorkerEventType
    job_id: str
    worker_run_id: str
    sequence: int
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.schema_version != WORKER_PROTOCOL_VERSION:
            raise ValueError(f"unsupported worker protocol version: {self.schema_version}")
        if not self.job_id.strip():
            raise ValueError("job_id must be non-empty")
        if not self.worker_run_id.strip():
            raise ValueError("worker_run_id must be non-empty")
        if self.sequence < 0:
            raise ValueError("sequence must be >= 0")

    def to_json_line(self) -> str:
        data: dict[str, object] = {
            "schema_version": self.schema_version,
            "event_type": self.event_type.value,
            "job_id": self.job_id,
            "worker_run_id": self.worker_run_id,
            "sequence": self.sequence,
            "payload": dict(self.payload),
        }
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n"

    @classmethod
    def from_json_line(cls, line: str) -> WorkerEnvelope:
        raw_object = cast(object, json.loads(line))
        if not isinstance(raw_object, dict):
            raise ValueError("worker event must be a JSON object")
        raw = cast(dict[str, object], raw_object)

        payload_object = raw.get("payload")
        if not isinstance(payload_object, dict):
            raise ValueError("worker event payload must be a JSON object")
        payload = cast(dict[str, object], payload_object)

        return cls(
            schema_version=_require_int(raw, "schema_version"),
            event_type=WorkerEventType(_require_str(raw, "event_type")),
            job_id=_require_str(raw, "job_id"),
            worker_run_id=_require_str(raw, "worker_run_id"),
            sequence=_require_int(raw, "sequence"),
            payload=payload,
        )
