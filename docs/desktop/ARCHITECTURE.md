# MeTube-SRT Desktop — Architecture Source of Truth

Authority: STEP 06 + STEP 07.

## Runtime

- Windows native desktop.
- Python 3.13 family.
- PySide6 / Qt Widgets.
- yt-dlp through an isolated child worker.
- FFmpeg/ffprobe external tools.
- yt-dlp EJS scripts plus a pinned Deno runtime in the portable package.
- Gemini via official `google-genai` adapter.
- Raw Gemini credentials via Windows Credential Locker/keyring.
- Durable operational data via SQLite; settings via atomic JSON.

## Dependency direction

```text
presentation   -> application -> domain
adapters       -> application -> domain
worker         -> application -> domain
infrastructure -> application -> domain
bootstrap      -> all layers (construction only)
```

## Invariants

- Widgets do not call yt-dlp, Gemini, SQLite, keyring, or subprocess directly.
- Domain imports no Qt/provider/storage/process implementation.
- Worker is disposable; parent application owns canonical job state.
- AI plan is untrusted until verified and, where required, approved.
- Manual and AI paths converge on the same application commands.
