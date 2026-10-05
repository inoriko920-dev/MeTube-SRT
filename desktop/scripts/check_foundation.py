from __future__ import annotations

from pathlib import Path


def main() -> int:
    desktop_root = Path(__file__).resolve().parents[1]
    required = [
        desktop_root / "pyproject.toml",
        desktop_root / "AGENTS.md",
        desktop_root / "src" / "metube_srt_desktop" / "__init__.py",
        desktop_root / "src" / "metube_srt_desktop" / "worker" / "protocol.py",
        desktop_root / "tests" / "contract" / "test_worker_protocol.py",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        for path in missing:
            print(f"MISSING: {path}")
        return 1
    print("STEP 08 desktop foundation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
