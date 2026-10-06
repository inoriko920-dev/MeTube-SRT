from __future__ import annotations

import pytest

from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset
from metube_srt_desktop.domain.subtitles import SubtitleKind, SubtitleTrack
from metube_srt_desktop.worker.yt_dlp_options import (
    build_download_options,
    build_resolve_options,
    build_subtitle_only_options,
)


def test_options_pin_explicit_deno_and_disable_remote_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deno = r"C:\Portable\tools\deno.exe"
    monkeypatch.setenv("METUBE_SRT_DENO_PATH", deno)

    resolve = build_resolve_options()
    download = build_download_options(
        JobSpec(
            job_id="job",
            source_url="https://www.youtube.com/watch?v=abc",
            output_directory=r"C:\Downloads",
            quality=QualityPreset.BEST,
            selected_subtitle=None,
        )
    )

    expected = {"deno": {"path": deno}}
    assert resolve["js_runtimes"] == expected
    assert download["js_runtimes"] == expected
    assert resolve["remote_components"] == set()
    assert download["remote_components"] == set()


def test_options_keep_deno_enabled_without_explicit_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("METUBE_SRT_DENO_PATH", raising=False)

    assert build_resolve_options()["js_runtimes"] == {"deno": {}}


def test_subtitle_only_options_do_not_redownload_media() -> None:
    job = JobSpec(
        job_id="job-sub",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory=r"C:\Downloads",
        quality=QualityPreset.P720,
        selected_subtitle=SubtitleTrack(
            language_code="id",
            kind=SubtitleKind.MANUAL,
            is_original=True,
        ),
    )

    media = build_download_options(job)
    subtitle = build_subtitle_only_options(job)

    assert media["writesubtitles"] is False
    assert media["writeautomaticsub"] is False
    assert "subtitleslangs" not in media

    assert subtitle["skip_download"] is True
    assert subtitle["writesubtitles"] is True
    assert subtitle["writeautomaticsub"] is False
    assert subtitle["subtitleslangs"] == ["id"]


def test_resolve_options_tolerate_unavailable_collection_entries() -> None:
    resolve = build_resolve_options(tolerate_unavailable_entries=True)

    assert resolve["ignoreerrors"] is True


def test_resolve_options_keep_single_video_errors_strict() -> None:
    resolve = build_resolve_options()

    assert resolve["ignoreerrors"] is False
