# Windows preview packaging

Target: Windows x64 standalone multi-file folder packaged as ZIP.

The preview build contains:

- `MeTube-SRT.exe` — windowed native desktop application;
- `MeTube-SRT-Worker.exe` — isolated worker process used by the typed NDJSON boundary;
- `tools/deno.exe`;
- `tools/ffmpeg.exe`;
- `tools/ffprobe.exe`;
- build metadata, preview instructions, and license.

This is deliberately a **preview/testing build**, not the final release claim. It exists so the
native manual path can be tested on a normal Windows network while GitHub-hosted YouTube access
is blocked by upstream anti-bot checks.

The main executable resolves its packaged worker as a sibling executable when frozen. The bootstrap
adds the sibling `tools` directory to PATH only for the frozen runtime.

Build locally on Windows after syncing dependencies and installing PyInstaller, Deno, and FFmpeg:

```powershell
.\packaging\build_windows_preview.ps1
```

CI workflow: `.github/workflows/desktop-windows-preview.yml`.

The produced ZIP is:

`desktop/build/windows-preview/MeTube-SRT-Windows-x64-Preview.zip`
