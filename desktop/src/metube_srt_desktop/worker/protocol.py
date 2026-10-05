"""Worker-side compatibility import for the application-owned IPC contract."""

from metube_srt_desktop.application.dto.worker_protocol import (
    WORKER_PROTOCOL_VERSION,
    WorkerEnvelope,
    WorkerEventType,
)

__all__ = ["WORKER_PROTOCOL_VERSION", "WorkerEnvelope", "WorkerEventType"]
