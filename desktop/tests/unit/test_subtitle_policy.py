from metube_srt_desktop.domain.subtitles import (
    SubtitleKind,
    SubtitleTrack,
    select_subtitle,
)


def track(
    code: str,
    kind: SubtitleKind,
    *,
    original: bool,
    translated: bool = False,
) -> SubtitleTrack:
    return SubtitleTrack(
        language_code=code,
        kind=kind,
        is_original=original,
        is_translated=translated,
    )


def test_original_manual_wins_over_auto_generated() -> None:
    manual = track("id", SubtitleKind.MANUAL, original=True)
    automatic = track("id", SubtitleKind.AUTO_GENERATED, original=True)

    assert select_subtitle((automatic, manual), requested=True) is manual


def test_non_translated_manual_still_wins_when_original_flag_is_unknown() -> None:
    manual = track("en", SubtitleKind.MANUAL, original=False)
    automatic = track("id", SubtitleKind.AUTO_GENERATED, original=True)

    assert select_subtitle((automatic, manual), requested=True) is manual


def test_translated_track_is_never_selected() -> None:
    translated_manual = track(
        "en",
        SubtitleKind.MANUAL,
        original=False,
        translated=True,
    )
    automatic = track("id", SubtitleKind.AUTO_GENERATED, original=True)

    assert select_subtitle((translated_manual, automatic), requested=True) is automatic


def test_unproven_auto_generated_track_is_not_guessed() -> None:
    automatic = track("en", SubtitleKind.AUTO_GENERATED, original=False)

    assert select_subtitle((automatic,), requested=True) is None


def test_subtitle_checkbox_off_always_returns_none() -> None:
    manual = track("id", SubtitleKind.MANUAL, original=True)

    assert select_subtitle((manual,), requested=False) is None
