from __future__ import annotations

from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset
from metube_srt_desktop.domain.subtitles import SubtitleKind

_RESOLUTION_SORT: dict[QualityPreset, str] = {
    QualityPreset.P1080: "res:1080",
    QualityPreset.P720: "res:720",
    QualityPreset.P480: "res:480",
}


def build_resolve_options() -> dict[str, object]:
    """Return metadata-only yt-dlp options for the isolated worker.

    Auto-translated YouTube subtitles are intentionally skipped at extraction time.
    """

    return {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "extractor_args": {"youtube": {"skip": ["translated_subs"]}},
    }


def build_download_options(job: JobSpec) -> dict[str, object]:
    """Translate an immutable JobSpec into explicit yt-dlp Python API options."""

    options: dict[str, object] = {
        "format": "bv*+ba/b",
        "paths": {"home": job.output_directory},
        "outtmpl": {"default": "%(title)s [%(id)s].%(ext)s"},
        "windowsfilenames": True,
        "noplaylist": True,
        "ignoreerrors": False,
        "continuedl": True,
        "writesubtitles": False,
        "writeautomaticsub": False,
    }

    resolution_sort = _RESOLUTION_SORT.get(job.quality)
    if resolution_sort is not None:
        options["format_sort"] = [resolution_sort]

    subtitle = job.selected_subtitle
    if subtitle is None:
        return options

    options["subtitleslangs"] = [subtitle.language_code]
    options["subtitlesformat"] = "srt/best"
    options["postprocessors"] = [
        {
            "key": "FFmpegSubtitlesConvertor",
            "format": "srt",
            "when": "before_dl",
        }
    ]

    if subtitle.kind is SubtitleKind.MANUAL:
        options["writesubtitles"] = True
    elif subtitle.kind is SubtitleKind.AUTO_GENERATED:
        options["writeautomaticsub"] = True

    return options
