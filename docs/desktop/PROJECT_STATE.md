# MeTube-SRT Desktop — Project State

## Verified baseline

- STEP 09 native app shell is merged on `main`.
- STEP 10 is active in pull request **#5 — Real download core foundation**.
- STEP 10 implementation is complete through native UI/runtime composition.
- Legacy web runtime remains present and protected.

## STEP 10 capabilities already implemented

The native manual path is wired without Gemini:

- typed single / playlist / channel resolve;
- frozen subtitle policy: manual/creator -> proven original auto-generated -> none;
- no automatic subtitle translation;
- isolated yt-dlp child worker with typed NDJSON protocol;
- parent subprocess adapter with stale-event and sequence validation;
- cooperative cancellation with terminate/kill escalation;
- application-owned job lifecycle;
- bounded queue scheduler;
- durable SQLite queue/restart recovery;
- resolve -> plan -> enqueue composition;
- Qt Download/Queue controller binding;
- real runtime composition from UI to resolver/queue/worker;
- progress, output, success, failure, cancellation, and interrupted state propagation.

## Core verification

At the last verified core checkpoint:

- Ruff format/lint: PASS;
- Pyright strict: PASS — 0 errors / 0 warnings;
- import-linter: PASS — 3 kept / 0 broken;
- pytest: PASS — 84 passed;
- foundation and package self-checks: PASS;
- STEP 09 screenshot regression: PASS;
- secret scan: PASS — 0 findings;
- legacy CI: PASS.

## Live qualification status

**BLOCKED_ENVIRONMENT on GitHub-hosted runners; not declared PASS.**

GitHub-hosted Windows runners were able to provision Deno and FFmpeg, but YouTube returned `LOGIN_REQUIRED / Sign in to confirm you’re not a bot` before public-video resolve completed. The same result was reproduced by invoking upstream yt-dlp directly against multiple current/public fixtures, so no MeTube-SRT protocol/state bug is inferred from that runner failure.

No account cookies, browser credentials, proxy secrets, or extractor bypasses were added to force a green CI result.

A local Windows qualification wrapper now exists for a normal/non-datacenter network. Its evidence ZIP is the required input to close the live-network portion of S10-001.

## Still out of scope for this checkpoint

- production FFmpeg/Deno portable staging;
- packaged worker/runtime publication;
- Gemini command execution and API-key rotation;
- updater/release publication;
- UI redesign.

## Next action

Run `desktop/scripts/run_live_qualification_windows.ps1` on a normal Windows network and review `desktop/build/live-qualification-evidence.zip`.

Do not advance to production tool staging or Gemini until the live manual path is genuinely qualified.
