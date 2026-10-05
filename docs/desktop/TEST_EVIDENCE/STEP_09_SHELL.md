# STEP 09 shell evidence

Task: S09-001 — Native app shell and global navigation.

Status at initial implementation commit: **IMPLEMENTED / CI PENDING**.

Expected evidence gate:

- PySide6 native QMainWindow starts without browser/WebEngine;
- global navigation labels exactly: Unduh / Antrian / API Gemini / Pengaturan;
- navigation changes QStackedWidget page;
- AI panel appears on Download page and can collapse;
- API-key and queue tables use Qt model/view fixtures;
- screenshot captured at 1440×900 on Windows CI;
- Ruff, Pyright strict, import-linter, pytest and secret gate remain green.

No live yt-dlp or Gemini call is part of S09-001.
