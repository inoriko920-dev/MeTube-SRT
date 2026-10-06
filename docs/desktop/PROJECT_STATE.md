# MeTube-SRT Desktop — Project State

## Current baseline

- STEP 09 native app shell remains merged on `main`.
- STEP 10 is active in pull request **#5 — Real download core foundation** on `step10/download-core`.
- ASTRA bug-audit baseline: `9686ca1ca40058f2b527b60ce88a63cab55305dc`.
- Stabilized desktop code baseline after SOL fixes: `825848fbb2123531b66861a31627ea5e383c5633`.
- Legacy web runtime remains present and protected; this batch did not redesign UI or replace the legacy Docker release.

## STEP 10 capabilities implemented

The native desktop path currently includes:

- typed single / playlist / channel resolve;
- recursive channel-tab traversal to unique leaf videos;
- frozen subtitle policy: manual/creator -> proven original auto-generated -> none;
- no automatic subtitle translation;
- isolated yt-dlp child worker with typed NDJSON protocol;
- bounded, durable SQLite queue/restart recovery;
- exclusive runtime ownership per data directory;
- active/pending target reservation to prevent overlapping writes for the same video+folder;
- verified final media/SRT output reporting;
- Qt Download/Queue controller binding;
- Gemini conversation with Keyring-backed profiles, cooldown handling, transport retry, and request-profile identity;
- conservative secret redaction including complete Cookie headers;
- Windows preview packaging with Deno/FFmpeg/ffprobe staging.

The AI panel remains a conversation/help surface. It is **not** yet a verified natural-language command executor for download actions.

## ASTRA B01–B07 stabilization status

| Bug | Result |
| --- | --- |
| B01 nested channel tabs treated as videos | IMPLEMENTED + VERIFIED_FIXTURE |
| B02 concurrent jobs can share one download target | IMPLEMENTED + VERIFIED_FIXTURE |
| B03 two runtimes can mutate one queue/database | IMPLEMENTED + VERIFIED_FIXTURE |
| B04 nonexistent output / unverified SRT reported as success | IMPLEMENTED + VERIFIED_FIXTURE |
| B05 late Gemini result updates the wrong key profile | IMPLEMENTED + VERIFIED_FIXTURE |
| B06 HTTPX transport failures bypass application retry | IMPLEMENTED + VERIFIED_FIXTURE |
| B07 Cookie header tail survives redaction | IMPLEMENTED + VERIFIED_FIXTURE |

These labels do **not** mean VERIFIED_LIVE. They mean the audited scenarios are covered by deterministic regression tests and the complete desktop CI gate is green on the stabilized code baseline.

## Deterministic verification

Desktop CI run **37504191788** on `825848fbb2123531b66861a31627ea5e383c5633`: **SUCCESS**.

- Ruff format: PASS;
- Ruff lint: PASS;
- Pyright strict: PASS;
- import-linter: PASS;
- pytest: **181 passed**;
- live qualification wrapper validation: PASS;
- foundation check: PASS;
- package self-check: PASS;
- STEP 09 screenshot capture: PASS;
- secret scan: PASS — 0 findings.

Legacy CI run **37504191498** on the same SHA: **SUCCESS**.

## Windows preview build

Desktop Windows Preview Build run **37504182757** on the same SHA: **SUCCESS**.

- artifact: `MeTube-SRT-Windows-x64-Preview`;
- artifact id: `11431501234`;
- artifact size: `224663914` bytes;
- artifact digest: `sha256:cf8331adf59d51a4e64fbf2415663ff16123fe33602570ead2a6246455c684c0`.

This proves the portable preview package can be built from the stabilized code. It does **not** by itself prove two-instance behavior, crash recovery, writable/fallback paths, Unicode paths, or real YouTube/Gemini behavior on a normal user PC.

## Windows / live qualification status

- **VERIFIED_FIXTURE:** PASS.
- **WINDOWS_BUILD:** PASS.
- **VERIFIED_WINDOWS behavioral qualification:** PENDING on a normal Windows PC.
- **VERIFIED_LIVE YouTube:** not declared PASS.
- Prior hosted-runner live qualification remains **BLOCKED_ENVIRONMENT** when YouTube returns `LOGIN_REQUIRED` / anti-bot responses.

Required normal-PC checks include:

- two instances against the same data directory;
- crash/restart and stale-lock recovery;
- cancellation during download/postprocessing;
- portable data directory and fallback directory;
- Unicode/spaces and non-writable output paths;
- single video, flat playlist, root channel with multiple tabs;
- SRT available and unavailable;
- final media/SRT existence/readability;
- Gemini overlap/out-of-order/cooldown/timeout cases using safe test profiles where available.

## Next action

Run the normal-PC Windows qualification from the stabilized build and record the evidence separately. Do not call the desktop release “stable” until those Windows/live gates are closed honestly.
