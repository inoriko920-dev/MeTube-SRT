# STEP 10 — ASTRA Bug Stabilization Evidence

Audit source: `00_ASTRA_BUG_AUDIT_PLAN_METUBE_SRT_2026-10-06.docx`

## Scope

ASTRA reproduced B01–B07 at audit baseline `9686ca1ca40058f2b527b60ce88a63cab55305dc`. SOL implemented the planned fixes on PR #5 without redesigning UI or changing the legacy Docker runtime.

Stabilized code baseline: `825848fbb2123531b66861a31627ea5e383c5633`.

## Bug disposition

- B01 nested channel leaf mapping — IMPLEMENTED + VERIFIED_FIXTURE.
- B02 atomic target reservation — IMPLEMENTED + VERIFIED_FIXTURE.
- B03 exclusive runtime/data-directory ownership — IMPLEMENTED + VERIFIED_FIXTURE.
- B04 final output and SRT verification — IMPLEMENTED + VERIFIED_FIXTURE.
- B05 Gemini request/profile identity — IMPLEMENTED + VERIFIED_FIXTURE.
- B06 HTTPX transport classification/retry — IMPLEMENTED + VERIFIED_FIXTURE.
- B07 full Cookie-header redaction — IMPLEMENTED + VERIFIED_FIXTURE.

## Deterministic gate

Desktop CI run: `37504191788` — SUCCESS.

- Ruff format: PASS.
- Ruff lint: PASS.
- Pyright strict: PASS.
- import-linter: PASS.
- pytest: 181 passed.
- live wrapper ValidateOnly: PASS.
- foundation script: PASS.
- package self-check: PASS.
- screenshot capture: PASS.
- secret scan: 0 findings.

Legacy CI run: `37504191498` — SUCCESS.

## Windows preview build

Run: `37504182757` — SUCCESS.

Artifact:
- name: `MeTube-SRT-Windows-x64-Preview`
- id: `11431501234`
- size: `224663914` bytes
- digest: `sha256:cf8331adf59d51a4e64fbf2415663ff16123fe33602570ead2a6246455c684c0`

## Remaining gates

The following are deliberately **not** marked PASS:

- normal-PC two-instance behavior;
- forced-crash stale-lock recovery;
- cancel during real download/postprocess;
- portable/fallback/read-only data paths;
- Unicode/spaces/non-writable output paths;
- live single/playlist/root-channel download on a normal network;
- real SRT available/unavailable outcome verification;
- real Gemini qualification when a configured user key is available.

Hosted YouTube anti-bot / `LOGIN_REQUIRED` is an environment blocker, not a substitute for normal-PC live evidence.

## Release statement

This batch closes the seven deterministic audit scenarios at fixture/CI level and produces a buildable Windows preview. It does **not** prove the entire application is bug-free and does not authorize a stable-release claim until the remaining Windows/live gates are recorded.
