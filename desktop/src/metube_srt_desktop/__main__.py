from __future__ import annotations

import argparse

from metube_srt_desktop import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metube-srt-desktop")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="Run the STEP 08 skeleton self-check without starting the future UI.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_check:
        print("MeTube-SRT Desktop skeleton: OK")
        return 0

    print(
        "MeTube-SRT Desktop UI is not implemented in STEP 08. "
        "Use --self-check for the repository foundation check."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
