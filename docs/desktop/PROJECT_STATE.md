# MeTube-SRT Desktop — Project State

## Verified baseline

- Factory step completed: **STEP 08 — Repository Skeleton & CI Foundation**.
- Owner for STEP 08: SOL.
- Starting main SHA: `70e43f058a2bdb0b9bd25d3a5c9fe6442807ec16`.
- STEP 08 working branch: `step08/desktop-skeleton`.
- Verified foundation commit before evidence checkpoint: `151b9e7706732dd7e04a15d04c259566aa27e176`.
- Windows Desktop CI run: `37258333680` — **SUCCESS**.
- Earlier full-gate run: `37258150918` — **SUCCESS**.
- Legacy web runtime remains present and protected.

## Verified STEP 08 capabilities

- isolated `desktop/` Python project exists;
- `desktop/uv.lock` exists and `uv lock --check` passes;
- CPython 3.13.16 installs on GitHub Windows runner;
- dependency sync succeeds;
- Ruff formatting and lint pass;
- Pyright strict passes with 0 errors / 0 warnings;
- all three import-linter architecture contracts pass;
- pytest: **9 passed**;
- foundation self-check passes;
- package `python -m metube_srt_desktop --self-check` passes;
- enforced detect-secrets gate reports 0 findings after generated caches are excluded;
- UI reference manifest contains exactly UI_01..UI_20 and records all 20 master PNG SHA-256 values.

## Toolchain locked for STEP 08 foundation

- CPython 3.13.16
- uv 0.12.22
- PySide6 6.11.2
- yt-dlp 2026.8.19
- google-genai 2.28.0
- keyring 25.7.0
- Ruff 0.16.10
- Pyright 1.1.414
- pytest 9.1.1
- pytest-qt 4.5.0
- import-linter 2.15
- detect-secrets 1.5.0

## Honest provisional items

- Only 10/20 frozen UI reference image bytes are currently stored in Git (`UI_04`, `UI_08`–`UI_16`).
- The remaining 10 frozen master images have authoritative filenames and SHA-256 values in the manifest, but their repository byte storage is still pending.
- No final Qt screen, live desktop yt-dlp download, live Gemini command execution, bundled FFmpeg/Deno package, or production updater is claimed verified yet.

## Next action

Proceed to **STEP 09 — App Shell / UI Implementation** using fixture data and the frozen UI contract. Do not begin full downloader/Gemini integration until the shell and UI states are verified.
