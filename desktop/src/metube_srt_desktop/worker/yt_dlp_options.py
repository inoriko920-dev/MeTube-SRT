from __future__ import annotations

import os

from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset
from metube_srt_desktop.domain.subtitles import SubtitleKind

_RESOLUTION_SORT: dict[QualityPreset, str] = {
    QualityPreset.P1080: "res:1080",
    QualityPreset.P720: "res:720",
    QualityPreset.P480: "res:480",
}


def build_resolve_options(
    *,
    tolerate_unavailable_entries: bool = False,
    force_single_video: bool = False,
) -> dict[str, object]:
    """Return metadata-only yt-dlp options for the isolated worker.

    Auto-translated YouTube subtitles are intentionally skipped at extraction time.
    """

    options: dict[str, object] = {
        **_javascript_runtime_options(),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "extract_flat": False,
        "ignoreerrors": tolerate_unavailable_entries,
        "extractor_args": {"youtube": {"skip": ["translated_subs"]}},
    }
    if force_single_video:
        options["noplaylist"] = True
    return options


def build_download_options(job: JobSpec) -> dict[str, object]:
    """Translate an immutable JobSpec into media-only yt-dlp options."""

    options: dict[str, object] = {
        **_javascript_runtime_options(),
        "format": "bv*+ba/b",
        "paths": {"home": job.output_directory},
        "outtmpl": {"default": "%(title)s [%(id)s].%(ext)s"},
        "windowsfilenames": True,
        "noplaylist": True,
        "ignoreerrors": False,
        "continuedl": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "writesubtitles": False,
        "writeautomaticsub": False,
    }

    resolution_sort = _RESOLUTION_SORT.get(job.quality)
    if resolution_sort is not None:
        options["format_sort"] = [resolution_sort]

    return options


def build_subtitle_only_options(job: JobSpec) -> dict[str, object]:
    """Build supplemental subtitle-only options for a selected original track."""

    subtitle = job.selected_subtitle
    if subtitle is None:
        raise ValueError("subtitle-only options require selected_subtitle")

    options: dict[str, object] = {
        **_javascript_runtime_options(),
        "paths": {"home": job.output_directory},
        "outtmpl": {"default": "%(title)s [%(id)s].%(ext)s"},
        "windowsfilenames": True,
        "noplaylist": True,
        "ignoreerrors": False,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "writesubtitles": False,
        "writeautomaticsub": False,
        "subtitleslangs": [subtitle.language_code],
        "subtitlesformat": "srt/best",
        "postprocessors": [
            {
                "key": "FFmpegSubtitlesConvertor",
                "format": "srt",
                "when": "before_dl",
            }
        ],
    }

    if subtitle.kind is SubtitleKind.MANUAL:
        options["writesubtitles"] = True
    elif subtitle.kind is SubtitleKind.AUTO_GENERATED:
        options["writeautomaticsub"] = True

    return options


def _javascript_runtime_options() -> dict[str, object]:
    deno_path = os.environ.get("METUBE_SRT_DENO_PATH", "").strip()
    deno_options: dict[str, object] = {}
    if deno_path:
        deno_options["path"] = deno_path
    return {
        "js_runtimes": {"deno": deno_options},
        "remote_components": set(),
    }
