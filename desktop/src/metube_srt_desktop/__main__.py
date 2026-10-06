from __future__ import annotations

import argparse
from collections.abc import Sequence

from metube_srt_desktop import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metube-srt-desktop")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Run the repository foundation check without starting the desktop UI.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args, qt_args = parser.parse_known_args(list(argv) if argv is not None else None)
    if args.self_check:
        from metube_srt_desktop.bootstrap.app_bootstrap import run_desktop

        if not callable(run_desktop):
            raise RuntimeError("desktop runtime bootstrap is unavailable")
        print("MeTube-SRT Desktop runtime imports: OK")
        return 0

    from metube_srt_desktop.bootstrap.app_bootstrap import run_desktop

    return run_desktop(qt_args)


if __name__ == "__main__":
    raise SystemExit(main())
