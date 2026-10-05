# MeTube-SRT Desktop — Product Source of Truth

## Product contract

A native Windows desktop downloader for single videos, playlists, and channels.

Core download remains usable without AI. Gemini is an optional agent that
interprets download intent and controls the same application commands available
to the manual UI.

## Subtitle contract

When SRT is enabled:

1. prefer manual/creator subtitle;
2. otherwise use a proven original auto-generated caption;
3. otherwise continue the video without subtitle;
4. never auto-translate.

Supplemental subtitle failure must not turn an otherwise successful video
download into a failed download.

## Non-goals for the desktop AI agent

It is not a transcription engine, translator, subtitle generator, summarizer,
arbitrary shell agent, or general computer-control agent.
