from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from metube_srt_desktop.bootstrap.app_bootstrap import _configure_portable_tools


def test_configure_portable_tools_prepends_explicit_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    monkeypatch.setenv("METUBE_SRT_TOOLS_DIR", str(tools_dir))
    monkeypatch.setenv("PATH", "existing")

    _configure_portable_tools()

    assert os.environ["PATH"].split(os.pathsep)[0] == str(tools_dir.resolve())


def test_configure_portable_tools_ignores_missing_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setenv("METUBE_SRT_TOOLS_DIR", str(missing))
    monkeypatch.setenv("PATH", "existing")

    _configure_portable_tools()

    assert os.environ["PATH"] == "existing"
