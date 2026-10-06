from __future__ import annotations

import shutil

import pytest
from scripts import qualify_live_ytdlp as qualification

from metube_srt_desktop.application.dto.download import ResolvedItem, ResolvedSource
from metube_srt_desktop.domain.jobs import SourceKind


def test_live_qualification_defaults_use_upstream_test_resources() -> None:
    assert qualification.DEFAULT_SINGLE_URL.endswith("BaW_jenozKc")
    assert "playlist?list=" in qualification.DEFAULT_PLAYLIST_URL
    assert "/@" in qualification.DEFAULT_CHANNEL_URL
    assert qualification.DEFAULT_CANCEL_URL != qualification.DEFAULT_SINGLE_URL
    assert qualification.DEFAULT_FAILURE_URL.startswith("https://www.youtube.com/watch?v=")


def test_assert_kind_requires_expected_collection_type() -> None:
    source = ResolvedSource(
        source_url="https://www.youtube.com/watch?v=BaW_jenozKc",
        kind=SourceKind.VIDEO,
        title="Test",
        items=(
            ResolvedItem(
                video_id="BaW_jenozKc",
                title="Test",
                webpage_url="https://www.youtube.com/watch?v=BaW_jenozKc",
            ),
        ),
    )

    qualification._assert_kind(source, SourceKind.VIDEO)

    with pytest.raises(qualification.QualificationError, match="expected playlist"):
        qualification._assert_kind(source, SourceKind.PLAYLIST)


def test_tool_version_reports_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda command: None)
    assert qualification._tool_version("missing-tool") == "missing"
