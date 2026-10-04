# STEP 06 — Architecture & Technology Decision
## MeTube-SRT Desktop — ASTRA v1.0

**Gate:** `PASS_WITH_PROVISIONAL`  
**UI source-of-truth:** STEP 05 frozen UI; repair anchor `f7b30614ff056c06f85c03bfc4f80cdefb7932b5`  
**Next:** STEP 07 — Code Constitution & Repository Architecture

## 1. Executive Decision

MeTube-SRT Desktop akan dibangun sebagai aplikasi desktop Python native-window menggunakan **PySide6 / Qt Widgets**. Runtime desktop final tidak memakai browser, localhost, web server, atau Docker.

`yt-dlp` tetap menjadi mesin ekstraksi/download utama, tetapi dijalankan dalam **child worker process** terpisah. UI tidak pernah menjalankan download/network/post-processing berat di UI thread. **FFmpeg/ffprobe** dibundel sebagai tool eksternal. Untuk YouTube modern, paket portable juga membundel **yt-dlp-ejs + Deno** agar aplikasi tidak bergantung pada runtime JavaScript yang sudah terpasang di PC pengguna.

AI Agent Gemini berada di application layer. AI hanya menafsirkan perintah download menjadi rencana terstruktur, diverifikasi, dipreview, dimintakan persetujuan bila perlu, lalu diterjemahkan menjadi command yang sama dengan UI manual. AI tidak boleh memanggil yt-dlp/shell langsung.

## 2. Frozen Product Constraints

- Desktop Windows sungguhan; bukan browser/localhost.
- Manual downloader adalah core product dan wajib berfungsi tanpa Gemini.
- Mendukung single video, playlist, dan channel.
- Subtitle: **manual/creator → original auto-generated → none**; never auto-translate.
- AI Agent hanya untuk download control/help, bukan transkripsi, penerjemahan, peringkasan, media analysis, atau subtitle generation.
- API Key Manager mendukung sampai 100 credential profile.
- Secret tidak boleh masuk log, DB biasa, screenshot, diagnostic, repo, atau exported settings.
- Portable ZIP multi-file adalah target release.
- 20 UI STEP 05 adalah visual contract.

## 3. ADR Summary

| ADR | Decision | Status |
|---|---|---|
| ADR-001 | PySide6 + Qt Widgets | SELECTED |
| ADR-002 | Ports/adapters + app-owned state | SELECTED |
| ADR-003 | yt-dlp Python API in child worker process | SELECTED |
| ADR-004 | yt-dlp-ejs + bundled Deno | SELECTED |
| ADR-005 | FFmpeg/ffprobe external tools | SELECTED |
| ADR-006 | MeTube-SRT subtitle policy engine | SELECTED |
| ADR-007 | Durable bounded queue/concurrency | SELECTED |
| ADR-008 | SQLite + atomic settings JSON | SELECTED |
| ADR-009 | Gemini official `google-genai` provider adapter | SELECTED |
| ADR-010 | 100-key Credential Locker profiles | SELECTED |
| ADR-011 | Cookie/auth provider boundary | SELECTED |
| ADR-012 | Central error/logging/redaction | SELECTED |
| ADR-013 | Standalone multi-file ZIP | SELECTED |
| ADR-014 | Desktop-specific GitHub Release updater | SELECTED BOUNDARY |

## 4. ADR-001 — Desktop UI

Use **PySide6 + Qt Widgets**.

- `QMainWindow` owns the shell.
- Global navigation remains: `Unduh / Antrian / API Gemini / Pengaturan`.
- Screens use stacked page routing, not URL routing.
- AI right panel is a resizable/collapsible region.
- Queue and key manager use `QTableView + QAbstractTableModel`.
- QSS/design tokens live centrally; per-screen ad-hoc styling is forbidden.
- DPI test targets: 100%, 125%, 150%, 200%.
- Do not use Qt WebEngine as the product shell.

## 5. ADR-002 — State Ownership & Layers

Canonical state belongs to MeTube-SRT, not widgets, yt-dlp, FFmpeg, Gemini, or credential backends.

Layer direction:

```text
ui -> application -> domain
       |       |
       |       +-> ports <- adapters
       +-> immutable DTO/events
```

Main layer ownership:

- `domain`: entities/enums/policies, no Qt/network/database imports.
- `application`: use cases, commands, queue orchestration.
- `ports`: download, AI, secret, cookie, storage, update interfaces.
- `adapters`: yt-dlp worker, Gemini, keyring, SQLite, updater.
- `ui`: Qt views/models/viewmodels only.
- `worker`: isolated resolve/download/post-process runtime.

## 6. ADR-003 — yt-dlp Worker Boundary

Use the **yt-dlp Python API** inside a separate child worker process.

- Resolver mode returns sanitized metadata without download.
- Download mode receives immutable `JobSpec`.
- Worker emits versioned NDJSON progress/result events.
- Parent application owns the durable job state.
- Use yt-dlp progress hooks/logger; do not scrape normal stdout.
- Each active job maps to one worker in v1.
- Cancellation first requests cooperative stop; hard terminate only after grace period.
- `.part` files can be preserved for resumability according to policy.
- yt-dlp is pinned per release; worker self-update is disabled.

## 7. ADR-004 — YouTube EJS / Deno

Portable builds bundle:

- matching `yt-dlp-ejs` package;
- pinned **Deno** runtime;
- explicit Deno path passed to yt-dlp.

Stable release does not depend on user PATH and does not need Node/Deno preinstalled. Remote EJS components are disabled by default when packaged EJS is present. Exact version pins are STEP 08 responsibilities.

## 8. ADR-005 — FFmpeg / ffprobe

FFmpeg and ffprobe are external bundled executables.

- Always pass explicit paths.
- Use for merge/remux/subtitle conversion/post-processing as required.
- Prefer an LGPL-compatible build without GPL/nonfree components unless licensing is intentionally changed.
- Store exact build provenance and third-party notices.

## 9. ADR-006 — Subtitle Policy

Subtitle selection is a domain policy, not an AI decision.

1. If manual/creator subtitle exists, prefer it.
2. Else use **proven original** auto-generated caption.
3. If an auto-caption exists but original/native track cannot be proven, do not guess.
4. If no acceptable subtitle exists, video download still succeeds.
5. Never auto-select translated captions and never auto-translate.

## 10. ADR-007 — Queue & Concurrency

Default simultaneous downloads: **2**. Initial supported setting may expose 1–4 after performance proof.

Job states:

`QUEUED / RESOLVING / RUNNING / POSTPROCESSING / CANCELLING / SUCCEEDED / FAILED / CANCELLED / INTERRUPTED`

Rules:

- UI thread never blocks on download/network/FFmpeg/large I/O.
- Every event carries `job_id` and `worker_run_id`.
- Late events from obsolete workers are rejected.
- Key testing is separately bounded (max 3 concurrent).

## 11. ADR-008 — Persistence

Use:

- **SQLite `app.db`**: jobs, queue order, history, output records, credential metadata references, last health state.
- **atomic `settings.json`**: UI preferences, output folder, quality, SRT default, concurrency, update channel.
- `logs/`: bounded redacted logs.
- `cache/`: disposable thumbnails/resolve cache.

Raw credentials never enter SQLite or settings JSON.

Portable mode uses a `portable.flag`. Data stays beside the app when writable; otherwise show an explicit fallback to LocalAppData.

## 12. ADR-009 — Gemini Provider

Use the official **`google-genai`** SDK behind `AIProviderPort`. Exact model ID/API variant is release configuration, not a UI contract.

Flow:

```text
INTERPRET -> VERIFY -> PREVIEW -> CONFIRM -> EXECUTE -> OBSERVE
```

Components:

- `AIController`
- `ContextBuilder`
- `AIProviderPort`
- `GeminiAdapter`
- `ToolRegistry`
- `PlanVerifier`
- `AICommandExecutor`

Rules:

- AI cannot construct arbitrary shell commands.
- AI cannot access raw API keys/cookies.
- AI cannot upload raw media in v1.
- Bulk actions require confirmation by default.
- AI reports success only after application/worker confirmation.

## 13. ADR-010 — 100 Gemini Key Profiles

Support up to **100 credential profiles**.

Raw key values live in **Windows Credential Locker** through Python `keyring`. SQLite stores only metadata: label, enabled, priority, project hint, last test, status, cooldown.

Failover:

- 401/invalid: mark invalid; try next safe enabled profile.
- transient network/5xx: exponential backoff, then failover if retry budget exhausted.
- 429: mark cooldown; do not assume another key increases quota.
- automatic 429 failover is allowed only for profiles explicitly marked as legitimately separate projects/accounts.
- same-project quota rotation is disabled by default.

100 profiles is management capacity, **not 100× quota**.

## 14. ADR-011 — Cookie / Authentication

Prefer browser-cookie integration or a user-owned Netscape cookie file reference.

- Store browser/profile descriptor or file path, not raw cookie values.
- Raw cookies never enter logs/SQLite.
- If future UX copies cookies into app storage, require DPAPI protection and a separate security review.

## 15. ADR-012 — Errors, Logs, Diagnostics

Error families: validation, resolve, auth, network, download, postprocess, filesystem, AI auth, AI rate limit, internal.

Central logging rules:

- redact before serialization;
- never log raw API key, cookie, Authorization header, token;
- diagnostic bundle includes dependency versions and redacted logs only;
- bounded retention.

## 16. ADR-013 — Portable Distribution

Use **`pyside6-deploy` / Nuitka `standalone` mode**, then package the output directory as ZIP.

Expected release contents include:

- `MeTube-SRT.exe`
- worker executable/runtime
- Qt DLLs/plugins
- Python runtime artifacts
- resources
- `tools/ffmpeg/`
- `tools/deno/`
- licenses / notices
- `portable.flag`

No installer and no single-EXE default.

## 17. ADR-014 — Update Strategy

Use desktop-specific GitHub Release manifest.

- Do not treat legacy web `v1.0.1` as a desktop update candidate.
- Download full ZIP in v1.
- Verify SHA-256.
- Update only after user approval.
- Run replacement from helper process after app exit.
- Keep rollback copy until the new package validates.

## 18. License Boundary

The repository currently uses **GNU AGPLv3**. STEP 06 does not relicense it.

- PySide6/Qt: LGPLv3/GPLv3/commercial choices; exact modules must be reviewed.
- yt-dlp source/Python package: Unlicense, with dependency inventory required.
- FFmpeg: LGPL baseline; GPL components change licensing obligations.
- Deno: MIT.
- exact package license inventory and notices are a release gate.

## 19. Performance Budgets

- startup target: <3s on normal SSD after first run;
- navigation: <100ms perceived;
- queue: smooth with ~1,000 rows using model/view;
- progress UI throttled ~4–10Hz;
- network/AI/resolve operations cancelable and never block UI;
- cache bounded.

## 20. Testing Architecture

- unit: subtitle policy, state transitions, plan verifier, key dispatch, path sanitizer;
- application integration: queue, repositories, redaction;
- worker contract: fake + real worker protocol;
- opt-in live yt-dlp: single/playlist/channel;
- AI: fake provider contract + optional live smoke;
- UI: `pytest-qt`;
- visual regression: 20 frozen STEP 05 references;
- packaging: fresh Windows VM;
- recovery: kill worker/app mid-download;
- security: secret scan, traversal, malicious AI payload.

## 21. Migration from Web Baseline

- Do not delete current web/Docker code during STEP 06–10.
- Desktop enters a separate subtree defined by STEP 07.
- Reuse proven product logic conceptually, especially subtitle policy; do not wrap web UI in a WebView.
- Web v1.0.1 remains historical baseline/evidence.
- Desktop becomes default only after STEP 10 proves a real native vertical slice.

## 22. Frozen vs Provisional

### Frozen

- PySide6 + Qt Widgets.
- App-owned state and ports/adapters.
- yt-dlp child worker.
- EJS + Deno requirement.
- FFmpeg/ffprobe external boundary.
- subtitle policy.
- SQLite + settings JSON + OS secret store.
- official `google-genai` provider adapter.

### Provisional until STEP 08

- exact Python/PySide6/yt-dlp/EJS/Deno/FFmpeg versions;
- exact Gemini model ID/API variant;
- updater helper implementation details;
- concurrency range above default 2.

## 23. Required Qualification Spikes

- `SPK-06-01`: standalone PySide6 ZIP launches on fresh Windows VM without Python/Qt/Docker installed.
- `SPK-06-02`: pinned yt-dlp + EJS + Deno resolves/downloads YouTube.
- `SPK-06-03`: video/playlist/channel + cancel/retry + FFmpeg merge.
- `SPK-06-04`: subtitle manual → original auto → none, with proof no auto-translate.
- `SPK-06-05`: 100-key metadata/Credential Locker/401/429 stress.
- `SPK-06-06`: Gemini structured plan → approval → queue command.
- `SPK-06-07`: update/rollback prototype with checksum.

## 24. Gate Decision

**STEP 06 GATE: `PASS_WITH_PROVISIONAL`**

Architecture is sufficiently defined for STEP 07. Remaining provisional items are exact dependency/model pins and packaging compatibility proof; none changes the UI freeze or major module boundaries.

## 25. Handoff to STEP 07

STEP 07 must define:

- repository tree / desktop subtree;
- code constitution;
- allowed dependency directions;
- module ownership;
- naming rules;
- DTO/event schemas;
- test placement;
- worker protocol ownership;
- rules preventing god-services and cross-layer imports.

### Current verification sources

- Qt for Python: https://doc.qt.io/qtforpython-6/
- pyside6-deploy: https://doc.qt.io/qtforpython-6.8/deployment/deployment-pyside6-deploy.html
- Qt licensing: https://doc.qt.io/qt-6/licensing.html
- yt-dlp: https://github.com/yt-dlp/yt-dlp
- yt-dlp EJS: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- FFmpeg legal: https://ffmpeg.org/legal.html
- Gemini getting started: https://ai.google.dev/gemini-api/docs/get-started
- Gemini API keys: https://ai.google.dev/gemini-api/docs/api-key
- Gemini rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Python keyring: https://keyring.readthedocs.io/en/stable/
- Deno license: https://github.com/denoland/deno/blob/main/LICENSE.md

Public moving facts verified 05 October 2026.
