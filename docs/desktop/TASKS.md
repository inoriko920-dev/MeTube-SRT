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

## READY

### S09-001 — Native app shell and global navigation

**Owner:** SOL  
**User outcome:** opening the desktop program shows a real PySide6 native window matching the frozen shell rather than a browser/web page.

**In scope**

- QMainWindow application shell;
- global navigation: Unduh / Antrian / API Gemini / Pengaturan;
- central stacked-page routing;
- right AI Agent panel shell/collapse behavior on relevant pages;
- central design tokens/QSS;
- reusable base components required by shell;
- fixture-only page states sufficient to compare UI_01..UI_20;
- UI tests and screenshot evidence.

**Out of scope**

- live yt-dlp download execution;
- live Gemini API calls;
- real credential storage implementation;
- FFmpeg/Deno staging;
- updater/release publication.

**ASTRA trigger**

Any frozen layout/navigation change, new top-level module, WebEngine/browser shell, dependency-direction change, or new material runtime dependency.
