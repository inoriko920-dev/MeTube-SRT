from collections.abc import Iterator

import pytest

from metube_srt_desktop.application.download_planning import (
    DownloadSelection,
    plan_download_jobs,
)
from metube_srt_desktop.application.dto.download import ResolvedItem, ResolvedSource
from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset, SourceKind
from metube_srt_desktop.domain.subtitles import SubtitleKind, SubtitleTrack


def subtitle(code: str, kind: SubtitleKind, *, original: bool) -> SubtitleTrack:
    return SubtitleTrack(language_code=code, kind=kind, is_original=original)


def id_factory(values: Iterator[str]) -> str:
    return next(values)


def test_playlist_expands_to_per_video_jobs_with_shared_selection() -> None:
    first_manual = subtitle("id", SubtitleKind.MANUAL, original=True)
    second_auto = subtitle("en", SubtitleKind.AUTO_GENERATED, original=True)
    source = ResolvedSource(
        source_url="https://www.youtube.com/playlist?list=PL123",
        kind=SourceKind.PLAYLIST,
        title="Playlist",
        items=(
            ResolvedItem(
                video_id="a",
                title="A",
                webpage_url="https://www.youtube.com/watch?v=a",
                subtitles=(first_manual,),
            ),
            ResolvedItem(
                video_id="b",
                title="B",
                webpage_url="https://www.youtube.com/watch?v=b",
                subtitles=(second_auto,),
            ),
        ),
    )
    ids = iter(("job-a", "job-b"))

    jobs = plan_download_jobs(
        source,
        DownloadSelection(
            output_directory=r"D:\Downloads",
            quality=QualityPreset.P1080,
            subtitle_requested=True,
        ),
        job_id_factory=lambda: id_factory(ids),
    )

    assert [job.job_id for job in jobs] == ["job-a", "job-b"]
    assert [job.source_url for job in jobs] == [
        "https://www.youtube.com/watch?v=a",
        "https://www.youtube.com/watch?v=b",
    ]
    assert all(job.quality is QualityPreset.P1080 for job in jobs)
    assert [job.selected_subtitle for job in jobs] == [first_manual, second_auto]


def test_subtitle_checkbox_off_propagates_to_every_item() -> None:
    manual = subtitle("id", SubtitleKind.MANUAL, original=True)
    source = ResolvedSource(
        source_url="https://www.youtube.com/@channel/videos",
        kind=SourceKind.CHANNEL,
        title="Channel",
        items=(
            ResolvedItem(
                video_id="a",
                title="A",
                webpage_url="https://www.youtube.com/watch?v=a",
                subtitles=(manual,),
            ),
            ResolvedItem(
                video_id="b",
                title="B",
                webpage_url="https://www.youtube.com/watch?v=b",
                subtitles=(manual,),
            ),
        ),
    )
    ids = iter(("job-a", "job-b"))

    jobs = plan_download_jobs(
        source,
        DownloadSelection(
            output_directory="Downloads",
            quality=QualityPreset.BEST,
            subtitle_requested=False,
        ),
        job_id_factory=lambda: id_factory(ids),
    )

    assert all(job.selected_subtitle is None for job in jobs)


def test_video_resolve_requires_exactly_one_item() -> None:
    with pytest.raises(ValueError, match="exactly one item"):
        ResolvedSource(
            source_url="https://www.youtube.com/watch?v=a",
            kind=SourceKind.VIDEO,
            title="Bad video resolve",
            items=(
                ResolvedItem(
                    video_id="a",
                    title="A",
                    webpage_url="https://www.youtube.com/watch?v=a",
                ),
                ResolvedItem(
                    video_id="b",
                    title="B",
                    webpage_url="https://www.youtube.com/watch?v=b",
                ),
            ),
        )


def test_job_spec_rejects_non_http_url_and_embedded_credentials() -> None:
    with pytest.raises(ValueError, match="absolute http"):
        JobSpec(
            job_id="job",
            source_url="not-a-url",
            output_directory="Downloads",
            quality=QualityPreset.BEST,
            selected_subtitle=None,
        )

    with pytest.raises(ValueError, match="embedded credentials"):
        JobSpec(
            job_id="job",
            source_url="https://user@example.com/video",
            output_directory="Downloads",
            quality=QualityPreset.BEST,
            selected_subtitle=None,
        )
