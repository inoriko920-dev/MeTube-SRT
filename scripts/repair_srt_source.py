#!/usr/bin/env python3
"""One-time deterministic repair for the initial MeTube-SRT bootstrap.

Removes a duplicated keyword introduced by the first overlay and ensures the
subtitle flag is propagated into each playlist/channel child item. It also
amends the reusable overlay script so future rebases do not recreate the bug.
"""

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


ytdl = Path("app/ytdl.py")
s = ytdl.read_text(encoding="utf-8")

s = replace_once(
    s,
    "                video_password=video_password,\n"
    "                download_subtitles=download_subtitles,\n"
    "            )\n"
    "            error = await self.__add_download(dl, auto_start)",
    "                video_password=video_password,\n"
    "            )\n"
    "            error = await self.__add_download(dl, auto_start)",
    "duplicate DownloadInfo keyword",
)

s = replace_once(
    s,
    "                        sponsorblock=sponsorblock,\n"
    "                        audio_tags=audio_tags,\n"
    "                        video_password=video_password,\n"
    "                    )\n"
    "                )\n"
    "            if any(res['status'] == 'error' for res in results):",
    "                        sponsorblock=sponsorblock,\n"
    "                        audio_tags=audio_tags,\n"
    "                        video_password=video_password,\n"
    "                        download_subtitles=download_subtitles,\n"
    "                    )\n"
    "                )\n"
    "            if any(res['status'] == 'error' for res in results):",
    "playlist/channel subtitle propagation",
)

ytdl.write_text(s, encoding="utf-8")

patch = Path("scripts/apply_patch.py")
p = patch.read_text(encoding="utf-8")
marker = 'print("MeTube-SRT patch applied successfully")'
if marker not in p:
    raise RuntimeError("apply_patch.py success marker not found")

if "Final normalization for shared MeTube call tails" not in p:
    normalization = r'''
# Final normalization for shared MeTube call tails. Earlier replacements touch
# similar call endings; these two targeted edits make the intended result
# explicit and reproducible on the pinned clean upstream source.
replace_once(
    "app/ytdl.py",
    '''                video_password=video_password,\n                download_subtitles=download_subtitles,\n            )\n            error = await self.__add_download(dl, auto_start)''',
    '''                video_password=video_password,\n            )\n            error = await self.__add_download(dl, auto_start)''',
)
replace_once(
    "app/ytdl.py",
    '''                        sponsorblock=sponsorblock,\n                        audio_tags=audio_tags,\n                        video_password=video_password,\n                    )\n                )\n            if any(res['status'] == 'error' for res in results):''',
    '''                        sponsorblock=sponsorblock,\n                        audio_tags=audio_tags,\n                        video_password=video_password,\n                        download_subtitles=download_subtitles,\n                    )\n                )\n            if any(res['status'] == 'error' for res in results):''',
)

'''
    p = p.replace(marker, normalization + marker, 1)
    patch.write_text(p, encoding="utf-8")

print("MeTube-SRT source repaired")
