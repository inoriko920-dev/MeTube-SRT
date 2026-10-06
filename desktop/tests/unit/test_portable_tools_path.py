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
    resolve_application_data_directory,
    run_desktop,
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


def test_configure_portable_tools_exports_explicit_deno_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    deno = tools_dir / ("deno.exe" if sys.platform == "win32" else "deno")
    deno.write_bytes(b"")
    monkeypatch.setenv("METUBE_SRT_TOOLS_DIR", str(tools_dir))
    monkeypatch.delenv("METUBE_SRT_DENO_PATH", raising=False)
    monkeypatch.setenv("PATH", "existing")

    configure_portable_tools()

    assert os.environ["METUBE_SRT_DENO_PATH"] == str(deno.resolve())


def test_resolve_application_data_directory_reports_local_app_data_fallback(
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

    directory, reported_fallback = resolve_application_data_directory()

    assert directory == fallback
    assert reported_fallback == fallback


def test_resolve_application_data_directory_has_no_fallback_when_writable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    app = tmp_path / "MeTube-SRT.exe"
    app.write_bytes(b"")
    (tmp_path / "portable.flag").write_text("portable", encoding="ascii")
    monkeypatch.delenv("METUBE_SRT_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(app))

    def writable(directory: Path) -> bool:
        return True

    monkeypatch.setattr(app_bootstrap, "_ensure_writable_directory", writable)

    directory, reported_fallback = resolve_application_data_directory()

    assert directory == tmp_path / "data"
    assert reported_fallback is None


def test_run_desktop_rejects_busy_data_directory_before_runtime_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    qapp: object,
) -> None:
    del qapp
    build_called = False
    warnings: list[tuple[object, ...]] = []

    class BusyRuntimeLock:
        def __init__(self, data_directory: Path) -> None:
            assert data_directory == tmp_path.resolve()

        def try_acquire(self) -> bool:
            return False

    def forbidden_build(*, data_directory: Path | None = None) -> object:
        nonlocal build_called
        build_called = True
        raise AssertionError(f"runtime build must not run for busy directory: {data_directory}")

    def capture_warning(*args: object, **kwargs: object) -> object:
        del kwargs
        warnings.append(args)
        return object()

    monkeypatch.setenv("METUBE_SRT_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(app_bootstrap, "RuntimeDataLock", BusyRuntimeLock)
    monkeypatch.setattr(app_bootstrap, "build_runtime_window", forbidden_build)
    monkeypatch.setattr(app_bootstrap.QMessageBox, "warning", capture_warning)

    assert run_desktop(["metube-srt-test"]) == 2
    assert build_called is False
    assert len(warnings) == 1
    assert "sudah berjalan" in str(warnings[0][1]).lower()
