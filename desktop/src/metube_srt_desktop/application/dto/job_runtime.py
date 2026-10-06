from __future__ import annotations

from dataclasses import dataclass

from metube_srt_desktop.domain.jobs import JobState


@dataclass(frozen=True, slots=True)
class JobRuntimeSnapshot:
    job_id: str
    worker_run_id: str
    state: JobState
    progress_percent: float | None = None
    downloaded_bytes: int | None = None
    total_bytes: int | None = None
    speed_bytes_per_second: float | None = None
    eta_seconds: float | None = None
    output_paths: tuple[str, ...] = ()
    warning_message: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    last_sequence: int | None = None

    def __post_init__(self) -> None:
        if not self.job_id.strip():
            raise ValueError("job_id must be non-empty")
        if not self.worker_run_id.strip():
            raise ValueError("worker_run_id must be non-empty")
        if self.progress_percent is not None and not 0 <= self.progress_percent <= 100:
            raise ValueError("progress_percent must be between 0 and 100")
        if self.downloaded_bytes is not None and self.downloaded_bytes < 0:
            raise ValueError("downloaded_bytes must be >= 0")
        if self.total_bytes is not None and self.total_bytes < 0:
            raise ValueError("total_bytes must be >= 0")
        if self.speed_bytes_per_second is not None and self.speed_bytes_per_second < 0:
            raise ValueError("speed_bytes_per_second must be >= 0")
        if self.eta_seconds is not None and self.eta_seconds < 0:
            raise ValueError("eta_seconds must be >= 0")
        if self.last_sequence is not None and self.last_sequence < 0:
            raise ValueError("last_sequence must be >= 0")
