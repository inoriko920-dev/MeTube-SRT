# MeTube-SRT Desktop — Project State

## Verified baseline

- Factory step completed: **STEP 09 — Native App Shell / UI Implementation**.
- STEP 08 foundation remains verified and preserved.
- STEP 09 working branch: `step09/app-shell`.
- Verified STEP 09 head before evidence checkpoint: `bd53a91fc4b7caa4260fe2ea07f96117ac4e5242`.
- Pull request: #4.
- Windows Desktop CI PR run: `37353004219` — **SUCCESS**.
- Legacy MeTube-SRT CI PR run: `37353004216` — **SUCCESS**.
- Legacy web runtime remains present and protected.

## Verified STEP 09 capabilities

- real native PySide6 `QMainWindow` exists;
- global navigation is fixed to Unduh / Antrian / API Gemini / Pengaturan;
- central routing uses `QStackedWidget`;
- Download page exposes the frozen SRT checkbox object contract;
- right AI Agent workspace shell exists and can collapse;
- Download / Queue / API Keys / Settings native fixture pages render;
- centralized design tokens and QSS exist;
- Pyright strict passes with 0 errors / 0 warnings;
- all three import-linter architecture contracts pass;
- pytest: **14 passed**;
- foundation self-check passes;
- package `python -m metube_srt_desktop --self-check` passes;
- Windows CI captures the STEP 09 shell screenshot at 1440×900;
- enforced detect-secrets gate reports 0 findings;
- legacy frontend/backend CI remains green.

## Toolchain currently locked

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
- The native UI is still fixture-driven; live desktop yt-dlp execution is not yet connected.
- Live Gemini command execution, real API-key storage/rotation, production FFmpeg/Deno bundling, updater, and release packaging are not yet verified.

## Locked product behavior for the next feature wave

- target remains a real Windows desktop app;
- single video, playlist, and channel downloads must remain supported;
- `Download subtitle (SRT)` is optional;
- creator/manual subtitle has priority;
- original auto-generated caption is the fallback;
- subtitles must never be auto-translated;
- lack of subtitles must not fail the video download.

## Next action

Proceed to **S10-001 — Real download core: resolve, enqueue, video + optional SRT**. Connect the native shell to the application/worker boundary using the locked subtitle policy. Do not begin Gemini command execution or redesign the frozen UI during this wave.
