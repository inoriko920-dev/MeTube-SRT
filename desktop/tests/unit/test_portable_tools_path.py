from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QStandardPaths

import metube_srt_desktop.bootstrap.app_bootstrap as app_bootstrap
from metube_srt_desktop.bootstrap.app_bootstrap import (
    application_data_directory,
    configure_portable_tools,
)


def test_configure_portable_tools_prepends_explicit_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    monkeypatch.setenv("METUBE_SRT_TOOLS_DIR", str(tools_dir))
    monkeypatch.setenv("PATH", "existing")

    configure_portable_tools()

    assert os.environ["PATH"].split(os.pathsep)[0] == str(tools_dir.resolve())


def test_configure_portable_tools_ignores_missing_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setenv("METUBE_SRT_TOOLS_DIR", str(missing))
    monkeypatch.setenv("PATH", "existing")

    configure_portable_tools()

    assert os.environ["PATH"] == "existing"


def test_application_data_directory_uses_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "explicit-data"
    monkeypatch.setenv("METUBE_SRT_DATA_DIR", str(target))

    assert application_data_directory() == target.resolve()
    assert target.is_dir()


def test_application_data_directory_uses_portable_folder_when_frozen(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app = tmp_path / "MeTube-SRT.exe"
    app.write_bytes(b"")
    (tmp_path / "portable.flag").write_text("portable", encoding="ascii")
    monkeypatch.delenv("METUBE_SRT_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(app))

    expected = tmp_path / "data"
    assert application_data_directory() == expected
    assert expected.is_dir()


def test_application_data_directory_falls_back_when_portable_is_not_writable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app = tmp_path / "MeTube-SRT.exe"
    app.write_bytes(b"")
    (tmp_path / "portable.flag").write_text("portable", encoding="ascii")
    fallback = tmp_path / "fallback"
    monkeypatch.delenv("METUBE_SRT_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(app))

    def not_writable(directory: Path) -> bool:
        return False

    def fallback_location(location: QStandardPaths.StandardLocation) -> str:
        return str(fallback)

    monkeypatch.setattr(app_bootstrap, "_ensure_writable_directory", not_writable)
    monkeypatch.setattr(QStandardPaths, "writableLocation", fallback_location)

    assert application_data_directory() == fallback
    assert fallback.is_dir()
