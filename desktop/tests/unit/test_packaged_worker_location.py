from __future__ import annotations

import os
import sys
from pathlib import Path

from metube_srt_desktop.adapters.download.subprocess_worker import _default_worker_argv


def test_default_worker_argv_uses_module_in_source_mode(monkeypatch) -> None:
    monkeypatch.delenv("METUBE_SRT_WORKER_EXE", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert _default_worker_argv() == (sys.executable, "-m", "metube_srt_desktop.worker")


def test_default_worker_argv_prefers_explicit_override(monkeypatch) -> None:
    monkeypatch.setenv("METUBE_SRT_WORKER_EXE", r"C:\Portable\MeTube-SRT-Worker.exe")

    assert _default_worker_argv() == (r"C:\Portable\MeTube-SRT-Worker.exe",)


def test_default_worker_argv_uses_sibling_worker_when_frozen(monkeypatch) -> None:
    monkeypatch.delenv("METUBE_SRT_WORKER_EXE", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Portable\MeTube-SRT.exe")

    expected = Path(r"C:\Portable\MeTube-SRT.exe").resolve().with_name(
        "MeTube-SRT-Worker.exe"
    )
    assert _default_worker_argv() == (str(expected),)
