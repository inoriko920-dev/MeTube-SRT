from __future__ import annotations

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
