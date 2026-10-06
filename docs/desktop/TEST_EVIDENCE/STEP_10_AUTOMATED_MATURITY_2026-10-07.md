# STEP 10 — Automated Maturity Evidence — 2026-10-07

## Authority

ASTRA audit source: `00_ASTRA_BUG_AUDIT_PLAN_METUBE_SRT_2026-10-06.docx`.

ASTRA B01–B07 stabilized code baseline: `825848fbb2123531b66861a31627ea5e383c5633`.

Latest automated maturity baseline: `261f1bd560667024389c508944896d2754344023`.

## Additional SOL hardening

Beyond B01–B07, SOL added deterministic checks for:

- cross-process runtime/data-directory exclusivity;
- stale lock recovery after forced owner-process termination;
- refusal of a busy data directory before runtime/database construction;
- Unicode and spaces in output paths;
- invalid output target failure without false output-success signaling;
- cancellation during postprocessing;
- re-extraction of the generated Windows ZIP;
- required archive file presence;
- packaged desktop self-check after extraction;
- packaged Windows credential self-check after extraction;
- packaged worker READY + CANCELLED smoke after extraction;
- BUILD_INFO source commit consistency.

## Verification

Desktop CI run `37513841827`: **SUCCESS**.

- Ruff format: PASS.
- Ruff lint: PASS.
- Pyright strict: 0 errors / 0 warnings.
- import-linter: 3 kept / 0 broken.
- pytest: **187 passed**.
- foundation/self-check/screenshot gates: PASS.
- secret scan: 0 findings.

Legacy MeTube-SRT CI run `37513841856`: **SUCCESS**.

Windows Preview Build run `37513834241`: **SUCCESS**.

Artifact:

- name: `MeTube-SRT-Windows-x64-Preview`
- id: `11436576507`
- size: `224666735` bytes
- digest: `sha256:a27e22969709609f0626e5e80d91b94d6562678cd480f85639a7f3dbde73e61d`

The build log records `=== Verify ZIP archive after extraction ===` followed by `Windows preview build: OK`.

## Honest remaining external gates

These cannot be converted into a truthful PASS from GitHub-hosted deterministic tests alone:

- real YouTube single/playlist/root-channel downloads on a non-datacenter network;
- real subtitle available/unavailable behavior against current YouTube responses;
- final media/SRT readability from those real downloads;
- actual Windows ACL-denied destination behavior on a restricted filesystem;
- real Gemini request with a valid user-configured API key.

Fresh hosted live qualification run `37514921314` reproduced the environment block after tool setup/verification passed: YouTube requested verification/login. Evidence artifact `11436712597` (`desktop-live-ytdlp-qualification`, digest `sha256:79ac3561798caaf4d85e7911a9082a56bd321a55284aae13849d47e4125cd78e`). This remains an environment limitation, not evidence of an application bug and not a live PASS.

## Release posture

The application is now hardened substantially beyond the original seven ASTRA bugs at deterministic/Windows-CI/package level. Do not claim the software is literally bug-free. S10 remains IN QUALIFICATION only for the genuinely external/live gates listed above.
