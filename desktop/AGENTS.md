# MeTube-SRT Desktop — AI / SOL Working Contract

This file governs the `desktop/` subtree.

## Read first

1. `../docs/desktop/PROJECT_STATE.md`
2. `../docs/desktop/TASKS.md`
3. `../docs/desktop/ARCHITECTURE.md`
4. `../docs/desktop/UI_SPEC.md` for UI work

## Non-negotiable

- Verify repository, branch, HEAD, active task, and parallel work before editing.
- Search before create; identify the owner module first.
- Preserve legacy `app/`, `ui/`, root `pyproject.toml`, Docker, and web release
  paths unless an explicit migration task says otherwise.
- UI_01 through UI_20 are frozen references. No silent redesign.
- No god file, generic `AppService`, `DownloadManager`, `AIManager`, or catch-all
  `utils.py`/`helpers.py`.
- `domain` imports no PySide6, yt-dlp, google-genai, database adapter, keyring,
  or UI/process infrastructure.
- `presentation` imports no concrete adapters.
- yt-dlp is reachable only through the download worker/adapter boundary.
- Gemini creates validated plans/commands and never executes shell/process
  commands or talks directly to the worker.
- Heavy work never blocks the Qt UI thread.
- Raw keys/cookies/tokens never enter repo, normal config, SQLite, logs,
  screenshots, or diagnostic exports.
- Report IMPLEMENTED versus VERIFIED accurately.

## Dependency direction

```text
presentation   -> application -> domain
adapters       -> application -> domain
worker         -> application -> domain
infrastructure -> application -> domain
bootstrap      -> all layers (construction only)
```

## Stop for ASTRA review

- new top-level layer/module family;
- dependency direction change;
- breaking worker protocol;
- new AI permission/tool family;
- secret/cookie storage strategy change;
- frozen UI structural change;
- material native/license-impacting dependency;
- legacy web removal or switch of default release product.
