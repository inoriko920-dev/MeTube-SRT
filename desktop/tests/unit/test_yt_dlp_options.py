from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset
from metube_srt_desktop.domain.subtitles import SubtitleKind, SubtitleTrack
from metube_srt_desktop.worker.yt_dlp_options import (
    build_download_options,
    build_resolve_options,
)


def make_job(
    *,
    quality: QualityPreset = QualityPreset.BEST,
    subtitle: SubtitleTrack | None = None,
) -> JobSpec:
    return JobSpec(
        job_id="job-1",
        source_url="https://www.youtube.com/watch?v=abc123",
        output_directory=r"D:\Downloads",
        quality=quality,
        selected_subtitle=subtitle,
    )


def test_resolve_options_skip_youtube_translated_subtitles() -> None:
    options = build_resolve_options()

    assert options["extract_flat"] is False
    assert options["extractor_args"] == {"youtube": {"skip": ["translated_subs"]}}


def test_best_quality_keeps_default_best_selector_without_resolution_cap() -> None:
    options = build_download_options(make_job())

    assert options["format"] == "bv*+ba/b"
    assert "format_sort" not in options


def test_quality_preset_uses_documented_resolution_sort_cap() -> None:
    options = build_download_options(make_job(quality=QualityPreset.P1080))

    assert options["format_sort"] == ["res:1080"]


def test_no_selected_subtitle_keeps_all_subtitle_writes_disabled() -> None:
    options = build_download_options(make_job())

    assert options["writesubtitles"] is False
    assert options["writeautomaticsub"] is False
    assert "subtitleslangs" not in options
    assert "postprocessors" not in options


def test_manual_subtitle_requests_only_manual_track_and_srt_conversion() -> None:
    subtitle = SubtitleTrack(
        language_code="en",
        kind=SubtitleKind.MANUAL,
        is_original=False,
    )

    options = build_download_options(make_job(subtitle=subtitle))

    assert options["writesubtitles"] is True
    assert options["writeautomaticsub"] is False
    assert options["subtitleslangs"] == ["en"]
    assert options["subtitlesformat"] == "srt/best"
    assert options["postprocessors"] == [
        {
            "key": "FFmpegSubtitlesConvertor",
            "format": "srt",
            "when": "before_dl",
        }
    ]


def test_auto_subtitle_requests_only_exact_original_auto_tag() -> None:
    subtitle = SubtitleTrack(
        language_code="id-orig",
        kind=SubtitleKind.AUTO_GENERATED,
        is_original=True,
    )

    options = build_download_options(make_job(subtitle=subtitle))

    assert options["writesubtitles"] is False
    assert options["writeautomaticsub"] is True
    assert options["subtitleslangs"] == ["id-orig"]


def test_each_job_is_forced_to_single_video_execution() -> None:
    options = build_download_options(make_job())

    assert options["noplaylist"] is True
    assert options["paths"] == {"home": r"D:\Downloads"}
    assert options["windowsfilenames"] is True
