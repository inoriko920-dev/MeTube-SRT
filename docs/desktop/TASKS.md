# MeTube-SRT Desktop — Task Queue

## DONE

### S08-001 — Desktop repository skeleton and CI foundation

**Owner:** SOL  
**Baseline:** STEP 07 + main `70e43f058a2bdb0b9bd25d3a5c9fe6442807ec16`  
**Verified CI:** run `37258333680` — SUCCESS

Delivered:

- isolated `desktop/` project and src-layout;
- exact dependency lock;
- desktop `AGENTS.md` and `docs/desktop/` source-of-truth;
- typed worker protocol scaffold;
- unit/contract skeleton tests;
- Ruff, Pyright strict, import-linter, pytest, pytest-qt environment, secret gate;
- independent Windows Desktop CI;
- UI_01..UI_20 reference manifest with master SHA-256 values;
- packaging/tool-manifest scaffold;
- legacy web path preserved.

Acceptance evidence:

- format: PASS;
- lint: PASS;
- type check: PASS — 0 errors, 0 warnings;
- import contracts: PASS — 3 kept, 0 broken;
- tests: PASS — 9 passed;
- foundation check: PASS;
- package self-check: PASS;
- secret gate: PASS — 0 findings;
- lock verification: PASS.

Known provisional evidence gap: 10/20 frozen UI image bytes are still pending Git storage. This does not authorize redesign; their master SHA-256 values are frozen in `UI_REFERENCES/manifest.json`.

### S09-001 — Native app shell and global navigation

**Owner:** SOL  
**Verified head:** `bd53a91fc4b7caa4260fe2ea07f96117ac4e5242`  
**Pull request:** #4  
**Desktop CI:** run `37353004219` — SUCCESS  
**Legacy CI:** run `37353004216` — SUCCESS

Delivered:

- native PySide6 `QMainWindow` shell;
- global navigation: Unduh / Antrian / API Gemini / Pengaturan;
- central `QStackedWidget` routing;
- right AI Agent workspace shell and collapse behavior;
- central design tokens / QSS;
- fixture-only Download / Queue / API Keys / Settings pages;
- UI and geometry tests;
- Windows screenshot evidence at 1440×900;
- stale STEP 08 no-shell assertion retired;
- secret-scan false positive fixed with a line-local allowlist annotation only.

Acceptance evidence:

- format: PASS;
- lint: PASS;
- type check: PASS — 0 errors, 0 warnings;
- import contracts: PASS — 3 kept, 0 broken;
- tests: PASS — 14 passed;
- foundation check: PASS;
- package self-check: PASS;
- screenshot capture: PASS;
- secret gate: PASS — 0 findings;
- screenshot artifact: `11363142258`.

## READY

### S10-001 — Real download core: resolve, enqueue, video + optional SRT

**Owner:** SOL  
**User outcome:** the native desktop app can accept a single video, playlist, or channel URL, resolve it, enqueue jobs, and execute real downloads without requiring Gemini.

**Locked subtitle behavior**

- `Download subtitle (SRT)` remains optional;
- prefer creator/manual subtitle when available;
- otherwise use original auto-generated caption when available;
- never auto-translate subtitles;
- if no subtitle exists, the video download still succeeds;
- subtitle selection must propagate correctly for playlist/channel jobs.

**In scope**

- connect Download page actions to application use cases;
- typed URL resolve result for single / playlist / channel;
- durable queue entries and job-state transitions;
- worker invocation boundary for yt-dlp;
- real video download execution;
- optional original SRT request and sidecar result handling;
- progress / success / failure events into Queue UI;
- cancellation boundary and restart-safe job metadata where already supported by the architecture;
- tests using fixtures/fakes plus narrowly scoped integration tests.

**Out of scope**

- Gemini command execution;
- API-key rotation logic;
- automatic subtitle translation;
- UI redesign outside the frozen contract;
- production FFmpeg/Deno bundling and updater/release publication.

**Current qualification status**

- implementation through native UI/runtime composition is complete on PR #5;
- deterministic core CI is green;
- GitHub-hosted live YouTube qualification is `BLOCKED_ENVIRONMENT` because upstream yt-dlp itself receives YouTube LOGIN_REQUIRED anti-bot responses;
- local Windows qualification wrapper/evidence bundle is the next required checkpoint;
- do not claim S10 live PASS until that evidence succeeds on a normal network.

**ASTRA trigger**

Any architecture-direction change, new top-level module, replacement of the worker boundary, subtitle-policy change, WebEngine/browser dependency, or new material runtime dependency.
