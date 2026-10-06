"""Parent-side adapters for the isolated yt-dlp worker process."""

from metube_srt_desktop.adapters.download.subprocess_worker import (
    SubprocessWorkerAdapter,
    WorkerAdapterError,
    WorkerProcessError,
    WorkerProtocolError,
)

__all__ = [
    "SubprocessWorkerAdapter",
    "WorkerAdapterError",
    "WorkerProcessError",
    "WorkerProtocolError",
]
