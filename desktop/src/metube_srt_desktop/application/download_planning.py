from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from metube_srt_desktop.application.dto.download import ResolvedSource
from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset
from metube_srt_desktop.domain.subtitles import select_subtitle


@dataclass(frozen=True, slots=True)
class DownloadSelection:
    output_directory: str
    quality: QualityPreset
    subtitle_requested: bool

    def __post_init__(self) -> None:
        if not self.output_directory.strip():
            raise ValueError("output_directory must be non-empty")


def plan_download_jobs(
    source: ResolvedSource,
    selection: DownloadSelection,
    *,
    job_id_factory: Callable[[], str],
) -> tuple[JobSpec, ...]:
    """Expand a resolved source into immutable per-video worker job specs."""

    jobs: list[JobSpec] = []
    for item in source.items:
        jobs.append(
            JobSpec(
                job_id=job_id_factory(),
                source_url=item.webpage_url,
                output_directory=selection.output_directory,
                quality=selection.quality,
                selected_subtitle=select_subtitle(
                    item.subtitles, requested=selection.subtitle_requested
                ),
            )
        )

    return tuple(jobs)
