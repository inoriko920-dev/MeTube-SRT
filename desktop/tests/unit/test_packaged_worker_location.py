from __future__ import annotations

import sys
from pathlib import Path

import pytest

from metube_srt_desktop.adapters.download.subprocess_worker import default_worker_argv


def testdefault_worker_argv_uses_module_in_source_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("METUBE_SRT_WORKER_EXE", raising=False)
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert default_worker_argv() == (sys.executable, "-m", "metube_srt_desktop.worker")


def testdefault_worker_argv_prefers_explicit_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("METUBE_SRT_WORKER_EXE", r"C:\Portable\MeTube-SRT-Worker.exe")

    assert default_worker_argv() == (r"C:\Portable\MeTube-SRT-Worker.exe",)


def testdefault_worker_argv_uses_sibling_worker_when_frozen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("METUBE_SRT_WORKER_EXE", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Portable\MeTube-SRT.exe")

    expected = Path(r"C:\Portable\MeTube-SRT.exe").resolve().with_name("MeTube-SRT-Worker.exe")
    assert default_worker_argv() == (str(expected),)



def test_default_worker_argv_prefers_packaged_worker_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app = tmp_path / "MeTube-SRT.exe"
    app.write_bytes(b"")
    worker_dir = tmp_path / "worker"
    worker_dir.mkdir()
    worker = worker_dir / "MeTube-SRT-Worker.exe"
    worker.write_bytes(b"")

    monkeypatch.delenv("METUBE_SRT_WORKER_EXE", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(app))

    assert default_worker_argv() == (str(worker.resolve()),)
