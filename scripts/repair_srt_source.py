#!/usr/bin/env python3
"""One-time repair for the initial MeTube-SRT bootstrap output."""

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


path = Path("app/ytdl.py")
text = path.read_text(encoding="utf-8")

# The initial overlay accidentally supplied download_subtitles twice to one
# DownloadInfo constructor. Keep the earlier keyword and remove this duplicate.
old = (
    "                video_password=video_password,\n"
    "                download_subtitles=download_subtitles,\n"
    "            )\n"
    "            error = await self.__add_download(dl, auto_start)"
)
new = (
    "                video_password=video_password,\n"
    "            )\n"
    "            error = await self.__add_download(dl, auto_start)"
)
text = replace_once(text, old, new, "duplicate DownloadInfo keyword")

# Propagate the checkbox into each playlist/channel child download.
old = (
    "                        sponsorblock=sponsorblock,\n"
    "                        audio_tags=audio_tags,\n"
    "                        video_password=video_password,\n"
    "                    )\n"
    "                )\n"
    "            if any(res['status'] == 'error' for res in results):"
)
new = (
    "                        sponsorblock=sponsorblock,\n"
    "                        audio_tags=audio_tags,\n"
    "                        video_password=video_password,\n"
    "                        download_subtitles=download_subtitles,\n"
    "                    )\n"
    "                )\n"
    "            if any(res['status'] == 'error' for res in results):"
)
text = replace_once(text, old, new, "playlist/channel subtitle propagation")

path.write_text(text, encoding="utf-8")
print("MeTube-SRT backend source repaired")
