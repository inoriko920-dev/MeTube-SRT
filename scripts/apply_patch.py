#!/usr/bin/env python3
"""Apply the small MeTube-SRT feature patch to a clean MeTube source tree.

The patch deliberately stays narrow: a video download may optionally ask yt-dlp
for an SRT sidecar. Manual subtitles win; if none exist, only the original
YouTube auto-caption track is accepted. Auto-translated caption tracks are
filtered out before yt-dlp selects subtitles.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()


def replace_once(relative: str, old: str, new: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{relative}: expected exactly 1 match, found {count}\n--- needle ---\n{old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def prepend_once(relative: str, marker: str, content: str) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    path.write_text(content + text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Backend: yt-dlp options for video + SRT sidecars
# ---------------------------------------------------------------------------
replace_once(
    "app/dl_formats.py",
    '''    subtitle_mode: str = "prefer_manual",\n    audio_tags: str = "with_cover",\n) -> dict:\n''',
    '''    subtitle_mode: str = "prefer_manual",\n    audio_tags: str = "with_cover",\n    download_subtitles: bool = False,\n) -> dict:\n''',
)

replace_once(
    "app/dl_formats.py",
    '''    if download_type == "captions":\n''',
    '''    if download_type == "video" and download_subtitles:\n        # MeTube-SRT: keep the normal video download and ask yt-dlp to write a\n        # subtitle sidecar at the same time. ``_ConfinedYoutubeDL`` filters the\n        # extractor subtitle dictionaries so auto-translated tracks never reach\n        # yt-dlp's subtitle selector.\n        opts["writesubtitles"] = True\n        opts["writeautomaticsub"] = True\n        opts["subtitleslangs"] = [".*"]\n        opts["subtitlesformat"] = "srt/best"\n        opts["metube_original_subtitles"] = True\n        postprocessors.append(\n            {\n                "key": "FFmpegSubtitlesConvertor",\n                "format": "srt",\n                "when": "before_dl",\n            }\n        )\n\n    if download_type == "captions":\n''',
)

# ---------------------------------------------------------------------------
# Backend: filter out YouTube auto-translation tracks before subtitle selection.
# Manual subtitles are preferred. If no manual subtitles exist, keep only the
# original auto-caption language (YouTube exposes it with ``-orig`` today).
# ---------------------------------------------------------------------------
replace_once(
    "app/ytdl.py",
    '''    def __init__(self, params=None, *, allowed_roots=(), **kwargs):\n        self._allowed_roots = [os.path.realpath(r) for r in allowed_roots if r]\n        super().__init__(params=params, **kwargs)\n\n    def prepare_filename(self, *args, **kwargs):\n''',
    '''    def __init__(self, params=None, *, allowed_roots=(), **kwargs):\n        self._allowed_roots = [os.path.realpath(r) for r in allowed_roots if r]\n        super().__init__(params=params, **kwargs)\n\n    def process_subtitles(self, video_id, normal_subtitles, automatic_captions):\n        if self.params.get("metube_original_subtitles"):\n            normal_subtitles = {\n                lang: formats\n                for lang, formats in (normal_subtitles or {}).items()\n                if lang != "live_chat"\n            }\n            automatic_captions = {\n                lang: formats\n                for lang, formats in (automatic_captions or {}).items()\n                if lang != "live_chat"\n            }\n\n            # A creator-provided subtitle is preferred over machine captions.\n            # If none exists, YouTube's original auto-caption track normally\n            # carries a ``-orig`` suffix. Translation tracks are intentionally\n            # discarded so this feature never asks YouTube for an auto-translate.\n            if normal_subtitles:\n                automatic_captions = {}\n            else:\n                originals = {\n                    lang: formats\n                    for lang, formats in automatic_captions.items()\n                    if lang.endswith("-orig")\n                }\n                if originals:\n                    automatic_captions = originals\n                elif len(automatic_captions) > 1:\n                    # Do not guess which one is original when an extractor does\n                    # not mark it. Avoiding accidental translation is safer.\n                    automatic_captions = {}\n\n        return super().process_subtitles(video_id, normal_subtitles, automatic_captions)\n\n    def prepare_filename(self, *args, **kwargs):\n''',
)

# Per-download state. Add the option at the end so old positional call sites and
# persisted records remain compatible.
replace_once(
    "app/ytdl.py",
    '''        audio_tags='with_cover',\n        video_password=None,\n    ):\n        self.id = id if len(custom_name_prefix) == 0 else f'{custom_name_prefix}.{id}'\n''',
    '''        audio_tags='with_cover',\n        video_password=None,\n        download_subtitles=False,\n    ):\n        self.id = id if len(custom_name_prefix) == 0 else f'{custom_name_prefix}.{id}'\n''',
)
replace_once(
    "app/ytdl.py",
    '''        self.subtitle_language = subtitle_language\n        self.subtitle_mode = subtitle_mode\n        self.ytdl_options_presets = list(ytdl_options_presets or [])\n''',
    '''        self.subtitle_language = subtitle_language\n        self.subtitle_mode = subtitle_mode\n        self.download_subtitles = bool(download_subtitles)\n        self.ytdl_options_presets = list(ytdl_options_presets or [])\n''',
)
replace_once(
    "app/ytdl.py",
    '''        if not hasattr(self, "subtitle_mode"):\n            self.subtitle_mode = "prefer_manual"\n        legacy_preset = self.__dict__.pop("ytdl_options_preset", None)\n''',
    '''        if not hasattr(self, "subtitle_mode"):\n            self.subtitle_mode = "prefer_manual"\n        if not hasattr(self, "download_subtitles"):\n            self.download_subtitles = False\n        legacy_preset = self.__dict__.pop("ytdl_options_preset", None)\n''',
)
replace_once(
    "app/ytdl.py",
    '''    "subtitle_language",\n    "subtitle_mode",\n    "ytdl_options_presets",\n''',
    '''    "subtitle_language",\n    "subtitle_mode",\n    "download_subtitles",\n    "ytdl_options_presets",\n''',
)
replace_once(
    "app/ytdl.py",
    '''            subtitle_language=getattr(info, 'subtitle_language', 'en'),\n            subtitle_mode=getattr(info, 'subtitle_mode', 'prefer_manual'),\n            audio_tags=getattr(info, 'audio_tags', 'with_cover'),\n''',
    '''            subtitle_language=getattr(info, 'subtitle_language', 'en'),\n            subtitle_mode=getattr(info, 'subtitle_mode', 'prefer_manual'),\n            audio_tags=getattr(info, 'audio_tags', 'with_cover'),\n            download_subtitles=getattr(info, 'download_subtitles', False),\n''',
)

# DownloadQueue.add: new option is keyword-friendly and defaults off.
replace_once(
    "app/ytdl.py",
    '''        sponsorblock=False,\n        audio_tags='with_cover',\n        video_password=None,\n    ):\n        if ytdl_options_presets is None:\n''',
    '''        sponsorblock=False,\n        audio_tags='with_cover',\n        video_password=None,\n        download_subtitles=False,\n    ):\n        if ytdl_options_presets is None:\n''',
)
replace_once(
    "app/ytdl.py",
    '''            f'{subtitle_language=} {subtitle_mode=} {ytdl_options_presets=} {clip_start=} {clip_end=} {sponsorblock=} {audio_tags=}'\n''',
    '''            f'{subtitle_language=} {subtitle_mode=} {download_subtitles=} {ytdl_options_presets=} {clip_start=} {clip_end=} {sponsorblock=} {audio_tags=}'\n''',
)

# Both early-add failures retain the setting for a later retry.
old_failure = '''                subtitle_language, subtitle_mode, ytdl_options_presets, ytdl_options_overrides,\n                clip_start, clip_end, retry_entry,\n            )'''
new_failure = '''                subtitle_language, subtitle_mode, ytdl_options_presets, ytdl_options_overrides,\n                clip_start, clip_end, retry_entry, download_subtitles=download_subtitles,\n            )'''
path = ROOT / "app/ytdl.py"
text = path.read_text(encoding="utf-8")
if text.count(old_failure) != 2:
    raise RuntimeError(f"app/ytdl.py: expected 2 add-failure call matches, found {text.count(old_failure)}")
path.write_text(text.replace(old_failure, new_failure), encoding="utf-8")

replace_once(
    "app/ytdl.py",
    '''            sponsorblock=sponsorblock,\n            audio_tags=audio_tags,\n            video_password=video_password,\n        )\n\n    async def retry(self, id):\n''',
    '''            sponsorblock=sponsorblock,\n            audio_tags=audio_tags,\n            video_password=video_password,\n            download_subtitles=download_subtitles,\n        )\n\n    async def retry(self, id):\n''',
)
replace_once(
    "app/ytdl.py",
    '''            audio_tags=info.audio_tags,\n            video_password=getattr(info, 'video_password', None),\n        )\n\n    async def add_entry(\n''',
    '''            audio_tags=info.audio_tags,\n            video_password=getattr(info, 'video_password', None),\n            download_subtitles=getattr(info, 'download_subtitles', False),\n        )\n\n    async def add_entry(\n''',
)

# Public add_entry helper (used by subscriptions) keeps default false, but can
# carry the option if a caller opts in later.
replace_once(
    "app/ytdl.py",
    '''        sponsorblock=False,\n        audio_tags='with_cover',\n    ):\n        if ytdl_options_presets is None:\n''',
    '''        sponsorblock=False,\n        audio_tags='with_cover',\n        download_subtitles=False,\n    ):\n        if ytdl_options_presets is None:\n''',
)
replace_once(
    "app/ytdl.py",
    '''            sponsorblock=sponsorblock,\n            audio_tags=audio_tags,\n        )\n\n    async def start_pending(self, ids):\n''',
    '''            sponsorblock=sponsorblock,\n            audio_tags=audio_tags,\n            download_subtitles=download_subtitles,\n        )\n\n    async def start_pending(self, ids):\n''',
)

# Internal entry walker: propagate through URL indirections and every playlist /
# channel child so one checkbox applies to the whole bulk add.
replace_once(
    "app/ytdl.py",
    '''        sponsorblock=False,\n        audio_tags='with_cover',\n        video_password=None,\n    ):\n        if not entry:\n''',
    '''        sponsorblock=False,\n        audio_tags='with_cover',\n        video_password=None,\n        download_subtitles=False,\n    ):\n        if not entry:\n''',
)

# There are two recursive propagation sites in __add_entry (URL and playlist child).
needle = '''                sponsorblock=sponsorblock,\n                audio_tags=audio_tags,\n                video_password=video_password,\n            )'''
replacement = '''                sponsorblock=sponsorblock,\n                audio_tags=audio_tags,\n                video_password=video_password,\n                download_subtitles=download_subtitles,\n            )'''
text = path.read_text(encoding="utf-8")
if text.count(needle) != 2:
    raise RuntimeError(f"app/ytdl.py: expected 2 recursive propagation matches, found {text.count(needle)}")
path.write_text(text.replace(needle, replacement), encoding="utf-8")

replace_once(
    "app/ytdl.py",
    '''                subtitle_language=subtitle_language,\n                subtitle_mode=subtitle_mode,\n                ytdl_options_presets=ytdl_options_presets,\n''',
    '''                subtitle_language=subtitle_language,\n                subtitle_mode=subtitle_mode,\n                download_subtitles=download_subtitles,\n                ytdl_options_presets=ytdl_options_presets,\n''',
)

# Failed-add record helper.
replace_once(
    "app/ytdl.py",
    '''        clip_start,\n        clip_end,\n        entry=None,\n    ):\n        """Surface a URL that failed before a DownloadInfo could be created''',
    '''        clip_start,\n        clip_end,\n        entry=None,\n        download_subtitles=False,\n    ):\n        """Surface a URL that failed before a DownloadInfo could be created''',
)
replace_once(
    "app/ytdl.py",
    '''            subtitle_language=subtitle_language,\n            subtitle_mode=subtitle_mode,\n            ytdl_options_presets=ytdl_options_presets,\n            ytdl_options_overrides=ytdl_options_overrides,\n            clip_start=clip_start,\n            clip_end=clip_end,\n        )\n        info.status = 'error'\n''',
    '''            subtitle_language=subtitle_language,\n            subtitle_mode=subtitle_mode,\n            download_subtitles=download_subtitles,\n            ytdl_options_presets=ytdl_options_presets,\n            ytdl_options_overrides=ytdl_options_overrides,\n            clip_start=clip_start,\n            clip_end=clip_end,\n        )\n        info.status = 'error'\n''',
)

# ---------------------------------------------------------------------------
# Backend HTTP API: boolean validation + /add plumbing.
# ---------------------------------------------------------------------------
replace_once(
    "app/main.py",
    '''    subtitle_language = post.get('subtitle_language')\n    subtitle_mode = post.get('subtitle_mode')\n    ytdl_options_overrides = post.get('ytdl_options_overrides')\n''',
    '''    subtitle_language = post.get('subtitle_language')\n    subtitle_mode = post.get('subtitle_mode')\n    download_subtitles = post.get('download_subtitles', False)\n    ytdl_options_overrides = post.get('ytdl_options_overrides')\n''',
)
replace_once(
    "app/main.py",
    '''    if not SUBTITLE_LANGUAGE_RE.fullmatch(subtitle_language):\n''',
    '''    if not isinstance(download_subtitles, bool):\n        raise web.HTTPBadRequest(reason='download_subtitles must be a boolean')\n    # The sidecar checkbox is intentionally a video-only option. Ignore a stale\n    # true value if an older/non-UI client changes the content type.\n    if download_type != 'video':\n        download_subtitles = False\n\n    if not SUBTITLE_LANGUAGE_RE.fullmatch(subtitle_language):\n''',
)
replace_once(
    "app/main.py",
    '''        'subtitle_language': subtitle_language,\n        'subtitle_mode': subtitle_mode,\n        'ytdl_options_presets': ytdl_options_presets,\n''',
    '''        'subtitle_language': subtitle_language,\n        'subtitle_mode': subtitle_mode,\n        'download_subtitles': download_subtitles,\n        'ytdl_options_presets': ytdl_options_presets,\n''',
)
replace_once(
    "app/main.py",
    '''        audio_tags=o['audio_tags'],\n        video_password=o['video_password'],\n    )\n''',
    '''        audio_tags=o['audio_tags'],\n        video_password=o['video_password'],\n        download_subtitles=o['download_subtitles'],\n    )\n''',
)

# ---------------------------------------------------------------------------
# Frontend request model/service.
# Optional on the service interface so existing callers/tests that construct a
# payload manually stay source-compatible; the main form always supplies it.
# ---------------------------------------------------------------------------
replace_once(
    "ui/src/app/services/downloads.service.ts",
    '''  subtitleLanguage: string;\n  subtitleMode: string;\n  ytdlOptionsPresets: string[];\n''',
    '''  subtitleLanguage: string;\n  subtitleMode: string;\n  downloadSubtitles?: boolean;\n  ytdlOptionsPresets: string[];\n''',
)
replace_once(
    "ui/src/app/services/downloads.service.ts",
    '''      subtitle_mode: payload.subtitleMode,\n      ytdl_options_presets: payload.ytdlOptionsPresets,\n''',
    '''      subtitle_mode: payload.subtitleMode,\n      ytdl_options_presets: payload.ytdlOptionsPresets,\n''',
)
replace_once(
    "ui/src/app/services/downloads.service.ts",
    '''    };\n    const cs = payload.clipStart?.trim();\n''',
    '''    };\n    if (payload.downloadSubtitles !== undefined) {\n      body['download_subtitles'] = payload.downloadSubtitles;\n    }\n    const cs = payload.clipStart?.trim();\n''',
)

# ---------------------------------------------------------------------------
# Frontend form state + cookie + payload.
# ---------------------------------------------------------------------------
replace_once(
    "ui/src/app/app.ts",
    '''  subtitleLanguage: string;\n  subtitleMode: string;\n  ytdlOptionsPresets: string[] = [];\n''',
    '''  subtitleLanguage: string;\n  subtitleMode: string;\n  downloadSubtitles: boolean;\n  ytdlOptionsPresets: string[] = [];\n''',
)
replace_once(
    "ui/src/app/app.ts",
    '''    this.subtitleLanguage = this.cookieService.get('metube_subtitle_language') || 'en';\n    this.subtitleMode = this.cookieService.get('metube_subtitle_mode') || 'prefer_manual';\n    this.ytdlOptionsPresets = this.loadYtdlOptionsPresetsFromCookie();\n''',
    '''    this.subtitleLanguage = this.cookieService.get('metube_subtitle_language') || 'en';\n    this.subtitleMode = this.cookieService.get('metube_subtitle_mode') || 'prefer_manual';\n    this.downloadSubtitles = this.cookieService.get('metube_download_subtitles') === 'true';\n    this.ytdlOptionsPresets = this.loadYtdlOptionsPresetsFromCookie();\n''',
)
replace_once(
    "ui/src/app/app.ts",
    '''  splitByChaptersChanged() {\n    this.cookieService.set('metube_split_chapters', this.splitByChapters ? 'true' : 'false', { expires: this.settingsCookieExpiryDays });\n  }\n\n  chapterTemplateChanged() {\n''',
    '''  splitByChaptersChanged() {\n    this.cookieService.set('metube_split_chapters', this.splitByChapters ? 'true' : 'false', { expires: this.settingsCookieExpiryDays });\n  }\n\n  downloadSubtitlesChanged() {\n    this.cookieService.set('metube_download_subtitles', this.downloadSubtitles ? 'true' : 'false', { expires: this.settingsCookieExpiryDays });\n  }\n\n  chapterTemplateChanged() {\n''',
)
replace_once(
    "ui/src/app/app.ts",
    '''      subtitleLanguage: overrides.subtitleLanguage ?? this.subtitleLanguage,\n      subtitleMode: overrides.subtitleMode ?? this.subtitleMode,\n      ytdlOptionsPresets: overrides.ytdlOptionsPresets ?? [...this.ytdlOptionsPresets],\n''',
    '''      subtitleLanguage: overrides.subtitleLanguage ?? this.subtitleLanguage,\n      subtitleMode: overrides.subtitleMode ?? this.subtitleMode,\n      downloadSubtitles:\n        (overrides.downloadType ?? this.downloadType) === 'video'\n          ? (overrides.downloadSubtitles ?? this.downloadSubtitles)\n          : false,\n      ytdlOptionsPresets: overrides.ytdlOptionsPresets ?? [...this.ytdlOptionsPresets],\n''',
)

# Visible, simple checkbox directly below the normal video format controls.
replace_once(
    "ui/src/app/app.html",
    '''      </div>\n\n      <div class="row mb-3 g-3">\n        <div class="col-12 text-start">\n          <button type="button"\n            class="btn btn-link p-0 text-decoration-none"\n''',
    '''      </div>\n\n      @if (downloadType === 'video') {\n        <div class="row mb-3">\n          <div class="col-12">\n            <div class="form-check form-switch">\n              <input class="form-check-input" type="checkbox" role="switch" id="checkbox-download-subtitles"\n                name="downloadSubtitles" [(ngModel)]="downloadSubtitles" (change)="downloadSubtitlesChanged()"\n                [disabled]="addInProgress || subscribeInProgress || downloads.loading">\n              <label class="form-check-label" for="checkbox-download-subtitles"\n                ngbPopover="Prefer creator-provided subtitles. If none exist, use the original auto-generated YouTube captions. Auto-translation is not requested."\n                triggers="hover" container="body">Download subtitle (SRT)</label>\n            </div>\n          </div>\n        </div>\n      }\n\n      <div class="row mb-3 g-3">\n        <div class="col-12 text-start">\n          <button type="button"\n            class="btn btn-link p-0 text-decoration-none"\n''',
)

# Small identity touch; no redesign.
replace_once(
    "ui/src/app/app.html",
    '''      MeTube\n    </a>\n''',
    '''      MeTube-SRT\n    </a>\n''',
)

# ---------------------------------------------------------------------------
# Regression test: video mode remains a real video download while enabling SRT.
# ---------------------------------------------------------------------------
replace_once(
    "app/tests/test_dl_formats.py",
    '''    def test_get_opts_captions_manual_only(self):\n''',
    '''    def test_get_opts_video_with_srt_sidecar(self):\n        opts = get_opts("video", "auto", "mp4", "best", {}, download_subtitles=True)\n        self.assertTrue(opts.get("writesubtitles"))\n        self.assertTrue(opts.get("writeautomaticsub"))\n        self.assertEqual(opts["subtitleslangs"], [".*"])\n        self.assertEqual(opts["subtitlesformat"], "srt/best")\n        self.assertTrue(opts.get("metube_original_subtitles"))\n        self.assertNotIn("skip_download", opts)\n        convertor = next(p for p in opts["postprocessors"] if p["key"] == "FFmpegSubtitlesConvertor")\n        self.assertEqual(convertor["format"], "srt")\n\n    def test_get_opts_captions_manual_only(self):\n''',
)

prepend_once(
    "README.md",
    "<!-- MeTube-SRT -->",
    '''<!-- MeTube-SRT -->\n# MeTube-SRT\n\nThis repository is a small derivative of MeTube that adds a **Download subtitle (SRT)** checkbox to normal video downloads. When enabled, creator-provided subtitles are preferred; if none exist, the original auto-generated YouTube caption track is used when available. MeTube-SRT does **not** request auto-translation. The option is propagated to every item when downloading a playlist or channel.\n\nThe exact upstream baseline is recorded in [`UPSTREAM_COMMIT`](UPSTREAM_COMMIT). Everything below this note is the upstream MeTube documentation.\n\n---\n\n''',
)

print("MeTube-SRT patch applied successfully")
