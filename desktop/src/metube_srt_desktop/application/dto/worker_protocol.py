from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from metube_srt_desktop.application.dto.download import ResolvedItem, ResolvedSource, ResolveRequest
from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset, SourceKind
from metube_srt_desktop.domain.subtitles import SubtitleKind, SubtitleTrack

WORKER_PROTOCOL_VERSION: Final[int] = 1


class WorkerCommandType(StrEnum):
    RESOLVE = "resolve"
    DOWNLOAD = "download"
    CANCEL = "cancel"


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


def _require_bool(raw: Mapping[str, object], key: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _optional_mapping(raw: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object or null")
    return cast(Mapping[str, object], value)


def _require_mapping_sequence(
    raw: Mapping[str, object], key: str
) -> tuple[Mapping[str, object], ...]:
    value = raw.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{key} must be an array")

    items: list[Mapping[str, object]] = []
    for item in cast(Sequence[object], value):
        if not isinstance(item, Mapping):
            raise ValueError(f"{key} must contain only objects")
        items.append(cast(Mapping[str, object], item))
    return tuple(items)


def _validate_identity(
    schema_version: int,
    job_id: str,
    worker_run_id: str,
    sequence: int | None = None,
) -> None:
    if schema_version != WORKER_PROTOCOL_VERSION:
        raise ValueError(f"unsupported worker protocol version: {schema_version}")
    if not job_id.strip():
        raise ValueError("job_id must be non-empty")
    if not worker_run_id.strip():
        raise ValueError("worker_run_id must be non-empty")
    if sequence is not None and sequence < 0:
        raise ValueError("sequence must be >= 0")


@dataclass(frozen=True, slots=True)
class WorkerCommandEnvelope:
    schema_version: int
    command_type: WorkerCommandType
    job_id: str
    worker_run_id: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        _validate_identity(self.schema_version, self.job_id, self.worker_run_id)

    def to_json_line(self) -> str:
        data: dict[str, object] = {
            "schema_version": self.schema_version,
            "command_type": self.command_type.value,
            "job_id": self.job_id,
            "worker_run_id": self.worker_run_id,
            "payload": dict(self.payload),
        }
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n"

    @classmethod
    def from_json_line(cls, line: str) -> WorkerCommandEnvelope:
        raw_object = cast(object, json.loads(line))
        if not isinstance(raw_object, dict):
            raise ValueError("worker command must be a JSON object")
        raw = cast(dict[str, object], raw_object)

        payload_object = raw.get("payload")
        if not isinstance(payload_object, dict):
            raise ValueError("worker command payload must be a JSON object")
        payload = cast(dict[str, object], payload_object)

        return cls(
            schema_version=_require_int(raw, "schema_version"),
            command_type=WorkerCommandType(_require_str(raw, "command_type")),
            job_id=_require_str(raw, "job_id"),
            worker_run_id=_require_str(raw, "worker_run_id"),
            payload=payload,
        )

    @classmethod
    def for_resolve(
        cls,
        request: ResolveRequest,
        *,
        job_id: str,
        worker_run_id: str,
    ) -> WorkerCommandEnvelope:
        return cls(
            schema_version=WORKER_PROTOCOL_VERSION,
            command_type=WorkerCommandType.RESOLVE,
            job_id=job_id,
            worker_run_id=worker_run_id,
            payload={"source_url": request.source_url},
        )

    @classmethod
    def for_download(cls, job: JobSpec, *, worker_run_id: str) -> WorkerCommandEnvelope:
        subtitle = job.selected_subtitle
        subtitle_payload: dict[str, object] | None = None
        if subtitle is not None:
            subtitle_payload = {
                "language_code": subtitle.language_code,
                "kind": subtitle.kind.value,
                "is_original": subtitle.is_original,
                "is_translated": subtitle.is_translated,
            }

        return cls(
            schema_version=WORKER_PROTOCOL_VERSION,
            command_type=WorkerCommandType.DOWNLOAD,
            job_id=job.job_id,
            worker_run_id=worker_run_id,
            payload={
                "source_url": job.source_url,
                "output_directory": job.output_directory,
                "quality": job.quality.value,
                "selected_subtitle": subtitle_payload,
            },
        )

    @classmethod
    def for_cancel(cls, *, job_id: str, worker_run_id: str) -> WorkerCommandEnvelope:
        return cls(
            schema_version=WORKER_PROTOCOL_VERSION,
            command_type=WorkerCommandType.CANCEL,
            job_id=job_id,
            worker_run_id=worker_run_id,
            payload={},
        )

    def as_resolve_request(self) -> ResolveRequest:
        if self.command_type is not WorkerCommandType.RESOLVE:
            raise ValueError("worker command is not a resolve command")
        return ResolveRequest(source_url=_require_str(self.payload, "source_url"))

    def as_job_spec(self) -> JobSpec:
        if self.command_type is not WorkerCommandType.DOWNLOAD:
            raise ValueError("worker command is not a download command")

        subtitle_raw = _optional_mapping(self.payload, "selected_subtitle")
        subtitle: SubtitleTrack | None = None
        if subtitle_raw is not None:
            subtitle = SubtitleTrack(
                language_code=_require_str(subtitle_raw, "language_code"),
                kind=SubtitleKind(_require_str(subtitle_raw, "kind")),
                is_original=_require_bool(subtitle_raw, "is_original"),
                is_translated=_require_bool(subtitle_raw, "is_translated"),
            )

        return JobSpec(
            job_id=self.job_id,
            source_url=_require_str(self.payload, "source_url"),
            output_directory=_require_str(self.payload, "output_directory"),
            quality=QualityPreset(_require_str(self.payload, "quality")),
            selected_subtitle=subtitle,
        )


@dataclass(frozen=True, slots=True)
class WorkerEnvelope:
    schema_version: int
    event_type: WorkerEventType
    job_id: str
    worker_run_id: str
    sequence: int
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        _validate_identity(self.schema_version, self.job_id, self.worker_run_id, self.sequence)

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


def resolved_source_to_payload(source: ResolvedSource) -> dict[str, object]:
    return {
        "source_url": source.source_url,
        "kind": source.kind.value,
        "title": source.title,
        "items": [
            {
                "video_id": item.video_id,
                "title": item.title,
                "webpage_url": item.webpage_url,
                "subtitles": [
                    {
                        "language_code": track.language_code,
                        "kind": track.kind.value,
                        "is_original": track.is_original,
                        "is_translated": track.is_translated,
                    }
                    for track in item.subtitles
                ],
            }
            for item in source.items
        ],
    }


def resolved_source_from_payload(payload: Mapping[str, object]) -> ResolvedSource:
    items: list[ResolvedItem] = []
    for item_raw in _require_mapping_sequence(payload, "items"):
        subtitles: list[SubtitleTrack] = []
        for track_raw in _require_mapping_sequence(item_raw, "subtitles"):
            subtitles.append(
                SubtitleTrack(
                    language_code=_require_str(track_raw, "language_code"),
                    kind=SubtitleKind(_require_str(track_raw, "kind")),
                    is_original=_require_bool(track_raw, "is_original"),
                    is_translated=_require_bool(track_raw, "is_translated"),
                )
            )
        items.append(
            ResolvedItem(
                video_id=_require_str(item_raw, "video_id"),
                title=_require_str(item_raw, "title"),
                webpage_url=_require_str(item_raw, "webpage_url"),
                subtitles=tuple(subtitles),
            )
        )

    return ResolvedSource(
        source_url=_require_str(payload, "source_url"),
        kind=SourceKind(_require_str(payload, "kind")),
        title=_require_str(payload, "title"),
        items=tuple(items),
    )
