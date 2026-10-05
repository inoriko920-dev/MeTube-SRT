from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Final, Mapping

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


@dataclass(frozen=True, slots=True)
class WorkerEnvelope:
    schema_version: int
    event_type: WorkerEventType
    job_id: str
    worker_run_id: str
    sequence: int
    payload: Mapping[str, Any]

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
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n"

    @classmethod
    def from_json_line(cls, line: str) -> "WorkerEnvelope":
        raw = json.loads(line)
        if not isinstance(raw, dict):
            raise ValueError("worker event must be a JSON object")
        payload = raw.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("worker event payload must be a JSON object")
        return cls(
            schema_version=int(raw["schema_version"]),
            event_type=WorkerEventType(str(raw["event_type"])),
            job_id=str(raw["job_id"]),
            worker_run_id=str(raw["worker_run_id"]),
            sequence=int(raw["sequence"]),
            payload=payload,
        )
