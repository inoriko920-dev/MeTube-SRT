from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from metube_srt_desktop.application.dto.queue_storage import PersistedQueueEntry


class QueueStorageError(RuntimeError):
    """Application-owned durable queue storage failure."""


class QueueStoragePort(Protocol):
    """Durable queue/history repository owned by the application boundary."""

    def load_entries(self) -> tuple[PersistedQueueEntry, ...]:
        """Load queue/history records ordered by stable queue position."""
        ...

    def save_entries(self, entries: Iterable[PersistedQueueEntry]) -> None:
        """Atomically insert or update the supplied queue/history records."""
        ...
