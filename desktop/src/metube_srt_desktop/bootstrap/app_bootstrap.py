from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication

from metube_srt_desktop.adapters.download import (
    SubprocessDownloadWorkerFactory,
    SubprocessSourceResolver,
)
from metube_srt_desktop.adapters.storage import SQLiteQueueStorage
from metube_srt_desktop.application.download_queue import BoundedDownloadQueue
from metube_srt_desktop.presentation.shell.main_window import MainWindow


def build_runtime_window(
    *,
    data_directory: Path | None = None,
) -> tuple[MainWindow, BoundedDownloadQueue]:
    _configure_portable_tools()
    directory = data_directory or _application_data_directory()
    storage = SQLiteQueueStorage(directory / "app.db")
    worker_factory = SubprocessDownloadWorkerFactory()
    queue = BoundedDownloadQueue.restore(worker_factory, storage)
    resolver = SubprocessSourceResolver()
    return MainWindow(resolver=resolver, queue=queue), queue


def run_desktop(argv: Sequence[str] | None = None) -> int:
    existing = QApplication.instance()
    owns_application = existing is None
    app = (
        QApplication(list(argv) if argv is not None else sys.argv) if existing is None else existing
    )
    if not isinstance(app, QApplication):
        raise RuntimeError("existing Qt application is not QApplication")

    app.setApplicationName("MeTube-SRT Desktop")
    app.setOrganizationName("MeTube-SRT")
    window, queue = build_runtime_window()
    app.aboutToQuit.connect(lambda: queue.shutdown(wait=False, cancel_active=True))
    window.show()

    if owns_application:
        return app.exec()
    return 0


def _application_data_directory() -> Path:
    raw_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    if not raw_path:
        raise RuntimeError("Qt did not provide an application data directory")
    return Path(raw_path)



def _configure_portable_tools() -> None:
    configured = os.environ.get("METUBE_SRT_TOOLS_DIR", "").strip()
    tools_directory: Path | None = Path(configured).expanduser() if configured else None

    if tools_directory is None and getattr(sys, "frozen", False):
        tools_directory = Path(sys.executable).resolve().parent / "tools"

    if tools_directory is None or not tools_directory.is_dir():
        return

    current_path = os.environ.get("PATH", "")
    tools_text = str(tools_directory.resolve())
    path_parts = [part for part in current_path.split(os.pathsep) if part]
    if tools_text.casefold() not in {part.casefold() for part in path_parts}:
        os.environ["PATH"] = os.pathsep.join((tools_text, *path_parts))
