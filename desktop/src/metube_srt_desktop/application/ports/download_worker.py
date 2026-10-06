from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from metube_srt_desktop.application.dto.worker_protocol import WorkerEnvelope


class DownloadWorkerError(RuntimeError):
    """Application-owned failure boundary for parent worker execution."""


class DownloadWorkerPort(Protocol):
    """Parent-side contract for one disposable download worker run."""

    def events(self) -> Iterable[WorkerEnvelope]:
        """Yield sanitized, ordered worker events."""
        ...

    def request_cancel(self) -> None:
        """Request cooperative cancellation without blocking the UI thread."""
        ...
