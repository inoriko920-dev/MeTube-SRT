# STEP 08 — Lock & Formatter Evidence

- Target branch: `step08/desktop-skeleton`
- Formatter/lock commit: `5626f83006b59648a1e977b6c34a6e7e25b87f58`
- CPython selected: 3.13.16
- uv selected: 0.12.23
- `uv lock`: PASS on Windows GitHub runner
- `uv sync --all-groups`: PASS on Windows GitHub runner
- Ruff formatter: applied successfully to desktop Python source/tests
- `desktop/uv.lock`: committed

This evidence does not claim the complete Desktop CI gate is green yet. The next Desktop CI run must verify format, lint, type, import architecture, tests, foundation check, self-check, and secret scan.
