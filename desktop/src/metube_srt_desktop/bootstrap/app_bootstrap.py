from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path
from tempfile import NamedTemporaryFile

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication

from metube_srt_desktop.adapters.ai import GeminiAdapter
from metube_srt_desktop.adapters.credentials import KeyringGeminiSecretStore
from metube_srt_desktop.adapters.download import (
    SubprocessDownloadWorkerFactory,
    SubprocessSourceResolver,
)
from metube_srt_desktop.adapters.storage import SQLiteQueueStorage
from metube_srt_desktop.adapters.storage.sqlite_gemini_profiles import (
    SQLiteGeminiProfileRepository,
)
from metube_srt_desktop.application.ai_conversation import HumanlikeAIConversation
from metube_srt_desktop.application.download_queue import BoundedDownloadQueue
from metube_srt_desktop.application.gemini_credentials import GeminiCredentialRegistry
from metube_srt_desktop.presentation.shell.main_window import MainWindow


def build_runtime_window(
    *,
    data_directory: Path | None = None,
) -> tuple[MainWindow, BoundedDownloadQueue]:
    configure_portable_tools()
    directory = data_directory or application_data_directory()
    database_path = directory / "app.db"
    storage = SQLiteQueueStorage(database_path)
    worker_factory = SubprocessDownloadWorkerFactory()
    queue = BoundedDownloadQueue.restore(worker_factory, storage)
    resolver = SubprocessSourceResolver()

    profile_repository = SQLiteGeminiProfileRepository(database_path)
    secret_store = KeyringGeminiSecretStore()
    credential_registry = GeminiCredentialRegistry(profile_repository, secret_store)
    ai_provider = GeminiAdapter(credential_registry.active_secret)
    ai_conversation = HumanlikeAIConversation(ai_provider)

    return (
        MainWindow(
            resolver=resolver,
            queue=queue,
            ai_conversation=ai_conversation,
            credential_registry=credential_registry,
            ai_provider=ai_provider,
        ),
        queue,
    )


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
    app.aboutToQuit.connect(lambda: queue.shutdown(wait=True, cancel_active=True))
    window.show()

    if owns_application:
        return app.exec()
    return 0


def application_data_directory() -> Path:
    configured = os.environ.get("METUBE_SRT_DATA_DIR", "").strip()
    if configured:
        directory = Path(configured).expanduser().resolve(strict=False)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    if getattr(sys, "frozen", False):
        app_directory = Path(sys.executable).resolve().parent
        if (app_directory / "portable.flag").is_file():
            portable_data = app_directory / "data"
            if _ensure_writable_directory(portable_data):
                return portable_data

    raw_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    if not raw_path:
        raise RuntimeError("Qt did not provide an application data directory")
    directory = Path(raw_path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _ensure_writable_directory(directory: Path) -> bool:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(prefix=".metube-write-", dir=directory, delete=True):
            pass
    except OSError:
        return False
    return True


def configure_portable_tools() -> None:
    configured = os.environ.get("METUBE_SRT_TOOLS_DIR", "").strip()
    tools_directory: Path | None = Path(configured).expanduser() if configured else None

    if tools_directory is None and getattr(sys, "frozen", False):
        tools_directory = Path(sys.executable).resolve().parent / "tools"

    if tools_directory is None or not tools_directory.is_dir():
        return

    deno_names = ("deno.exe", "deno") if sys.platform == "win32" else ("deno", "deno.exe")
    for name in deno_names:
        deno_path = tools_directory / name
        if deno_path.is_file():
            os.environ["METUBE_SRT_DENO_PATH"] = str(deno_path.resolve())
            break

    current_path = os.environ.get("PATH", "")
    tools_text = str(tools_directory.resolve())
    path_parts = [part for part in current_path.split(os.pathsep) if part]
    if tools_text.casefold() not in {part.casefold() for part in path_parts}:
        os.environ["PATH"] = os.pathsep.join((tools_text, *path_parts))
