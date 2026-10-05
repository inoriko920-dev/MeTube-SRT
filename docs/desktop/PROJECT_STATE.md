# MeTube-SRT Desktop — Project State

## Verified baseline

- Factory step: STEP 08 — Repository Skeleton & CI Foundation.
- Owner: SOL.
- Starting repository branch: `main`.
- Starting verified HEAD: `70e43f058a2bdb0b9bd25d3a5c9fe6442807ec16`.
- Working branch: `step08/desktop-skeleton`.
- Legacy web runtime remains present and protected.

## Current implementation claim

STEP 08 skeleton is being materialized. No final UI, live yt-dlp desktop
integration, Gemini execution, API-key UI, or release package is claimed
verified until its own evidence exists.

## Toolchain proposal pending Windows CI proof

- CPython 3.13.16
- uv 0.12.23
- PySide6 6.11.2
- yt-dlp 2026.8.19
- google-genai 2.28.0
- keyring 25.7.0

## Next evidence

1. Generate `desktop/uv.lock`.
2. Run desktop Windows CI: format/lint/type/import/tests/foundation.
3. Verify UI reference manifest.
4. Record CI run and commit SHA.
