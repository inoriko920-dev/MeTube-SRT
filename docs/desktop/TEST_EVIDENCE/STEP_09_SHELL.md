# STEP 09 — Native App Shell Evidence

Task: S09-001 — Native app shell and global navigation.

Status: **VERIFIED / PASS**.

## Verified implementation

- native PySide6 `QMainWindow` starts without browser/WebEngine;
- global navigation labels are exactly: Unduh / Antrian / API Gemini / Pengaturan;
- navigation routes through `QStackedWidget` pages;
- AI Agent workspace is visible on Download and supports collapse behavior;
- Download, Queue, API Keys, and Settings use fixture-only native Qt states;
- screenshot capture succeeds at 1440×900 on Windows CI;
- legacy web application remains protected and its CI still passes.

## Acceptance evidence

- verified head: `bd53a91fc4b7caa4260fe2ea07f96117ac4e5242`;
- pull request: #4;
- Desktop CI PR run: `37353004219` — **SUCCESS**;
- MeTube-SRT CI PR run: `37353004216` — **SUCCESS**;
- Ruff format: PASS;
- Ruff lint: PASS;
- Pyright strict: PASS — 0 errors / 0 warnings;
- import-linter: PASS — 3 contracts kept / 0 broken;
- pytest: PASS — 14 passed;
- foundation script: PASS;
- package self-check: PASS;
- screenshot capture: PASS;
- detect-secrets: PASS — 0 findings after a local allowlist annotation for the non-secret UI enum identifier `API_KEYS`;
- screenshot artifact ID: `11363142258`;
- screenshot artifact digest: `sha256:0ffd81dc60bd40f9a15285cdc4bbee44831933b48d027ec725a543167c053edf`.

## Scope boundary

S09-001 does not claim live yt-dlp execution, live Gemini API calls, real credential storage, FFmpeg/Deno staging, updater, or release packaging. Those remain later feature waves.
