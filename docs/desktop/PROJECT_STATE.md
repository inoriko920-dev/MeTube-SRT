# MeTube-SRT Desktop — Project State

## Current baseline

- STEP 09 native app shell remains merged on `main`.
- STEP 10 is active in pull request **#5 — Real download core foundation** on `step10/download-core`.
- ASTRA bug-audit baseline: `9686ca1ca40058f2b527b60ce88a63cab55305dc`.
- ASTRA B01–B07 stabilized code baseline: `825848fbb2123531b66861a31627ea5e383c5633`.
- Latest automated maturity baseline: `261f1bd560667024389c508944896d2754344023`.
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

Desktop CI run **37513841827** on `261f1bd560667024389c508944896d2754344023`: **SUCCESS**.

- Ruff format: PASS;
- Ruff lint: PASS;
- Pyright strict: PASS;
- import-linter: PASS;
- pytest: **187 passed**;
- live qualification wrapper validation: PASS;
- foundation check: PASS;
- package self-check: PASS;
- STEP 09 screenshot capture: PASS;
- secret scan: PASS — 0 findings.

Legacy CI run **37513841856** on the same SHA: **SUCCESS**.

## Windows preview build

Desktop Windows Preview Build run **37513834241** on the same SHA: **SUCCESS**.

- artifact: `MeTube-SRT-Windows-x64-Preview`;
- artifact id: `11436576507`;
- artifact size: `224666735` bytes;
- artifact digest: `sha256:a27e22969709609f0626e5e80d91b94d6562678cd480f85639a7f3dbde73e61d`;
- packaged desktop self-check: PASS before ZIP and after re-extraction;
- packaged credential self-check: PASS before ZIP and after re-extraction;
- packaged worker READY/CANCELLED smoke: PASS before ZIP and after re-extraction;
- required archive structure + BUILD_INFO source SHA: PASS.

This proves the portable preview package can be built from the stabilized code. It does **not** by itself prove two-instance behavior, crash recovery, writable/fallback paths, Unicode paths, or real YouTube/Gemini behavior on a normal user PC.

## Windows / live qualification status

- **VERIFIED_FIXTURE:** PASS.
- **WINDOWS_BUILD:** PASS.
- **VERIFIED_WINDOWS behavioral qualification:** PENDING on a normal Windows PC.
- **VERIFIED_LIVE YouTube:** not declared PASS.
- Prior hosted-runner live qualification remains **BLOCKED_ENVIRONMENT** when YouTube returns `LOGIN_REQUIRED` / anti-bot responses.

Automated Windows/fixture qualification now also covers:

- exclusive runtime lock across separate processes on Windows CI;
- stale-lock recovery after forced owner-process termination;
- bootstrap refusal before runtime/database construction when the data directory is busy;
- cancellation during postprocessing plus existing download cancellation boundaries;
- portable data directory and LocalAppData fallback selection;
- Unicode/spaces output directories;
- invalid output target failure without false OUTPUT_READY/SUCCESS;
- Gemini profile-bound late-result handling, cooldown preservation, transport retry, and cancellation;
- ZIP re-extraction and packaged self/credential/worker smoke.

Still requires genuine external/live evidence rather than simulation:

- real YouTube single video, flat playlist, and root channel with multiple tabs on a non-datacenter network;
- real SRT available/unavailable outcomes and final media/SRT readability from YouTube;
- Windows ACL-denied/non-writable destination behavior on a real restricted filesystem;
- real Gemini request using a user-configured valid API key.

## Next action

Keep S10-001 in qualification for the genuinely external/live gates above. The deterministic application, Windows CI, packaging, lock/crash, path, cancellation, queue, Gemini-race, and archive gates are green; do not mislabel hosted YouTube anti-bot blocking as an application failure or as a live PASS.
