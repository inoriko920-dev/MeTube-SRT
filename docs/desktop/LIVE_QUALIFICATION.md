# Slice 10 — Local Live Qualification (Windows)

This qualification is intentionally run from a normal Windows network rather than a GitHub-hosted datacenter runner. GitHub-hosted Windows runners were proven to receive YouTube `LOGIN_REQUIRED / Sign in to confirm you’re not a bot` even when upstream yt-dlp is invoked directly.

## What this validates

The script uses the real MeTube-SRT subprocess boundary and checks:

- single-video resolve;
- playlist resolve;
- channel resolve;
- original subtitle selection without auto-translation;
- a real video + SRT download;
- live progress and output-ready events;
- cooperative cancellation;
- sanitized expected-failure handling.

This is qualification evidence only. It does not introduce production packaging or Gemini execution.

## Prerequisites

Run on Windows with these commands available on `PATH`:

- `uv`
- `deno`
- `ffmpeg`
- `ffprobe`

The desktop Python environment is created by `uv sync --all-groups`.

## Run

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\desktop\scripts\run_live_qualification_windows.ps1
```

Or from inside `desktop`:

```powershell
.\scripts\run_live_qualification_windows.ps1
```

For repeated runs after dependencies are already synced:

```powershell
.\scripts\run_live_qualification_windows.ps1 -SkipSync
```

The wrapper does not read browser cookies, account credentials, proxy secrets, or Gemini keys.

## Evidence

The run produces:

- `desktop/build/live-qualification-local/report.json`
- `desktop/build/live-qualification-local/qualification.log`
- `desktop/build/live-qualification-local/upstream-probe.log` when qualification fails
- `desktop/build/live-qualification-local/summary.txt`
- `desktop/build/live-qualification-evidence.zip`

Downloaded test media stays outside the evidence ZIP.

If the app qualification fails, the wrapper also invokes upstream yt-dlp directly against the public single-video fixture. This distinguishes an application failure from a YouTube/network anti-bot block.

## Optional fixture overrides

Set any of these environment variables before running when a default public fixture changes:

- `METUBE_LIVE_SINGLE_URL`
- `METUBE_LIVE_PLAYLIST_URL`
- `METUBE_LIVE_CHANNEL_URL`
- `METUBE_LIVE_SRT_URL`
- `METUBE_LIVE_CANCEL_URL`
- `METUBE_LIVE_FAILURE_URL`

A successful local run is required before Slice 10 can be called live-qualified.
