# MeTube-SRT Desktop

Native Windows desktop line for MeTube-SRT.

This subtree is intentionally isolated from the legacy web application in the
repository root (`app/`, `ui/`, Docker runtime). During STEP 08 the desktop
project contains only an enforceable skeleton, architecture contracts, tests,
and CI foundation.

## Current factory state

- STEP 05 UI: frozen.
- STEP 06 architecture: frozen with provisional exact runtime pins.
- STEP 07 code constitution: frozen.
- STEP 08: repository skeleton and CI foundation.

No full downloader, Gemini feature, or final UI screen is claimed complete yet.

## Development commands

From `desktop/`:

```powershell
uv sync --all-groups
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run lint-imports
uv run pytest
uv run detect-secrets scan --all-files --exclude-files 'uv\.lock'
```

The lockfile is generated and verified by STEP 08 Windows CI before it becomes
the dependency authority.
