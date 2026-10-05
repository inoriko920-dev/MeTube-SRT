# STEP 07 — Code Constitution & Repository Architecture

**Project:** MeTube-SRT Desktop  
**Status:** PASS_WITH_PROVISIONAL  
**Architecture authority:** STEP 06  
**UI authority:** STEP 05 frozen contract  
**Verified repo baseline at authoring:** `main` @ `090e7288305558f18cc7212d08f1ba7f5e842fd6`

## Executive constitution

Desktop source is isolated under `desktop/`. Existing `app/`, `ui/`, root `pyproject.toml`, Docker/web runtime, and legacy release path remain untouched until a later explicit migration decision.

Dependency direction:

```text
presentation  ---> application ---> domain
adapters      ---> application ---> domain
worker        ---> application ---> domain
infrastructure---> application ---> domain
bootstrap     ---> all layers (construction only)
```

## Canonical top-level desktop structure

```text
desktop/
  AGENTS.md
  README.md
  pyproject.toml
  uv.lock
  src/metube_srt_desktop/
    bootstrap/
    domain/
    application/
    presentation/
    adapters/
    worker/
    infrastructure/
  resources/
  tools/manifests/
  scripts/
  packaging/
  tests/
docs/desktop/
  PRODUCT.md
  UI_SPEC.md
  ARCHITECTURE.md
  PROJECT_STATE.md
  TASKS.md
  DECISIONS/
  TEST_EVIDENCE/
  UI_REFERENCES/manifest.json
```

Do not create meaningless empty packages. STEP 08 materializes only enforceable skeleton pieces.

## Non-negotiable rules

- Verify repo/branch/HEAD before editing.
- Search before create and identify owner module.
- Preserve legacy web source during STEP 08–10.
- No business rules in Qt widgets.
- Domain imports no PySide6, yt-dlp, google-genai, sqlite adapters, keyring, or subprocess UI glue.
- Presentation imports no concrete adapters.
- yt-dlp is reachable only through download-worker boundaries.
- Gemini produces validated plans/commands; it never invokes shell/worker directly.
- Manual and AI actions share the same application command path.
- Worker never owns canonical database state.
- Raw Gemini keys live only in Windows Credential Locker.
- No blind same-project key rotation as a quota bypass.
- No silent UI redesign: UI_01–UI_20 remain frozen.
- No generic god `Manager`, `Service`, or catch-all `utils.py`.

## Size review triggers

| Trigger | Review |
|---|---|
| Python file > ~400 logical lines | mixed capability/owner? |
| Class > ~250 lines | coordinator plus business logic? |
| Function > ~60 lines | validation/mapping/I/O should split? |
| Qt screen/controller > ~300 lines | viewmodel/components missing? |
| > 7–8 constructor deps | god coordinator? |

## Core module ownership

| Owner | Owns | Must not own |
|---|---|---|
| `domain/jobs` | job intent/state invariants | Qt, DB, yt-dlp dict |
| `domain/subtitles` | manual -> original auto -> none policy | AI/UI/raw URL |
| `application` | commands, queries, use-cases, ports | concrete SDKs |
| `presentation` | Qt state/layout/viewmodels | yt-dlp/Gemini/sqlite/keyring |
| `adapters/download` | parent worker adapter | widgets |
| `worker` | yt-dlp execution + typed events | canonical DB state |
| `adapters/ai` | google-genai mapping | direct job mutation |
| `adapters/credentials` | Credential Locker | raw-key logging |
| `adapters/storage` | SQLite/settings | dialogs |
| `bootstrap` | dependency composition | feature logic |

## Worker contract

IPC payloads are typed/versioned and carry at minimum:
`schema_version`, `event_type`, `job_id`, `worker_run_id`, `sequence`, and sanitized `payload`.

Late events from an old `worker_run_id` are stale and must not mutate current state.

## AI contract

`INTERPRET -> VERIFY -> PREVIEW -> CONFIRM -> APPLICATION COMMAND -> OBSERVE`

Gemini is not a transcription, translation, subtitle-generation, summarization, or arbitrary computer-control layer.

## Source of truth

- `desktop/AGENTS.md` — desktop AI/SOL working contract
- `docs/desktop/PRODUCT.md`
- `docs/desktop/UI_SPEC.md`
- `docs/desktop/ARCHITECTURE.md`
- `docs/desktop/PROJECT_STATE.md`
- `docs/desktop/TASKS.md`
- `docs/desktop/DECISIONS/`
- `docs/desktop/TEST_EVIDENCE/`
- `docs/desktop/UI_REFERENCES/manifest.json`

## STEP 08 acceptance blueprint

1. Re-verify live repo baseline and collisions.
2. Pin coherent desktop Python/PySide6 toolchain after compatibility check.
3. Create minimal `desktop/` src-layout.
4. Create source-of-truth docs.
5. Add format/lint/type/pytest/pytest-qt/import-contract/secret gates.
6. Add worker protocol scaffold with fake/contract tests.
7. Add independent Windows desktop CI.
8. Create UI_01–UI_20 reference manifest and checksums/pointers.
9. Add packaging/tool manifest scaffold.
10. Update PROJECT_STATE/TASKS with evidence.

**Do not implement full screens, full yt-dlp/Gemini integration, or delete legacy web source in STEP 08.**

## Gate

**PASS_WITH_PROVISIONAL** — architecture is complete enough for SOL to create the enforceable skeleton. Exact dependency versions, CI evidence, packaging proof, and runtime qualification belong to STEP 08+.
