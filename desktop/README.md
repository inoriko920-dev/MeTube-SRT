# MeTube-SRT Desktop

Native Windows desktop line for MeTube-SRT.

This subtree is intentionally isolated from the legacy web application in the
repository root (`app/`, `ui/`, Docker runtime). During STEP 08 the desktop
project contains only an enforceable skeleton, architecture contracts, tests,
and CI foundation.

## Current factory state

- STEP 05 UI: frozen.
- STEP 06 architecture: frozen.
- STEP 07 code constitution: frozen.
- STEP 08 repository foundation: complete.
- STEP 09 native app shell: complete and merged.
- STEP 10 real manual download core: implemented through UI/runtime composition; live-network qualification is still open because GitHub-hosted runners are blocked by YouTube anti-bot checks.

Gemini execution and production portable tool staging are not part of the current qualification checkpoint.

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


## Live qualification on Windows

Run this only from a normal/non-datacenter Windows network:

```powershell
.\scripts\run_live_qualification_windows.ps1
```

The result is packaged as `build/live-qualification-evidence.zip`. See `docs/desktop/LIVE_QUALIFICATION.md` for details.
