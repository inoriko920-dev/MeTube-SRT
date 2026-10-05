# STEP 08 — Repository Skeleton & CI Foundation Evidence

## Baseline

- Repository: `inoriko920-dev/MeTube-SRT`
- Starting main SHA: `70e43f058a2bdb0b9bd25d3a5c9fe6442807ec16`
- Working branch: `step08/desktop-skeleton`
- Verified foundation commit: `151b9e7706732dd7e04a15d04c259566aa27e176`
- Windows CI run: `37258333680`
- Result: **SUCCESS**

## Gate evidence

| Gate | Result |
| --- | --- |
| uv 0.12.22 setup | PASS |
| CPython 3.13.16 install | PASS |
| `uv lock --check` | PASS |
| `uv sync --all-groups` | PASS |
| Ruff format | PASS |
| Ruff lint | PASS |
| Pyright strict | PASS — 0 errors, 0 warnings |
| import-linter | PASS — 3 contracts kept, 0 broken |
| pytest | PASS — 9 passed |
| foundation script | PASS |
| package self-check | PASS |
| enforced secret scan | PASS — 0 findings |
| lock artifact/upload step | PASS |

## Important corrections made during STEP 08

1. Corrected unavailable uv `0.12.23` proposal to released `0.12.22`.
2. Made worker protocol typing strict instead of weakening Pyright.
3. Moved the worker IPC contract into Application DTO ownership after import-linter correctly detected Application -> Worker dependency leakage.
4. Changed secret scanning so candidate findings cause CI failure; generated virtualenv/cache files are excluded.

## UI reference evidence

- Manifest IDs: **20/20** (`UI_01`–`UI_20`).
- Master SHA-256 recorded: **20/20**.
- Reference bytes currently in Git: **10/20** (`UI_04`, `UI_08`–`UI_16`).
- Remaining 10 image bytes: pending repository storage; visual content remains frozen and may not be redesigned.

## STEP 08 gate

**PASS_WITH_PROVISIONAL**

Repository skeleton and CI foundation are verified and sufficient to proceed to STEP 09. The remaining provisional item is repository storage completeness for ten frozen UI master/reference images; it is an evidence/storage gap, not an architecture or UI-design gap.
