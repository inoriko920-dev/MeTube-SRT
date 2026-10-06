from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QMessageBox

from metube_srt_desktop.application.gemini_credentials import GeminiCredentialRegistry
from metube_srt_desktop.application.ports.ai_provider import AIProviderError, AIProviderPort
from metube_srt_desktop.application.ports.credentials import CredentialStorageError
from metube_srt_desktop.presentation.pages.api_keys.page import ApiKeysPage


@dataclass(frozen=True, slots=True)
class _CheckResult:
    error: Exception | None


class _CheckSignals(QObject):
    finished = Signal(object)


class _CheckTask(QRunnable):
    def __init__(self, call: Callable[[], None]) -> None:
        super().__init__()
        self._call = call
        self.signals = _CheckSignals()

    @Slot()
    def run(self) -> None:
        try:
            self._call()
            result = _CheckResult(None)
        except Exception as exc:
            result = _CheckResult(exc)
        self.signals.finished.emit(result)


class GeminiCredentialsController(QObject):
    def __init__(
        self,
        page: ApiKeysPage,
        registry: GeminiCredentialRegistry,
        provider: AIProviderPort,
        *,
        parent: QObject | None = None,
        thread_pool: QThreadPool | None = None,
    ) -> None:
        super().__init__(parent)
        self._page = page
        self._registry = registry
        self._provider = provider
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._tasks: set[_CheckTask] = set()

        self._page.add_button.clicked.connect(self.add_key)
        self._page.import_button.clicked.connect(self.import_keys)
        self._page.test_button.clicked.connect(self.test_active_key)
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        try:
            self._page.set_profiles(self._registry.list_profiles())
        except CredentialStorageError:
            self._page.set_profiles(())

    @Slot()
    def add_key(self) -> None:
        label, ok = QInputDialog.getText(
            self._page,
            "Tambah API Gemini",
            "Nama key:",
        )
        if not ok:
            return
        raw_key, ok = QInputDialog.getText(
            self._page,
            "Tambah API Gemini",
            "API key:",
            QLineEdit.EchoMode.Password,
        )
        if not ok:
            return
        try:
            self._registry.add_profile(label, raw_key)
        except (ValueError, CredentialStorageError) as exc:
            QMessageBox.warning(self._page, "API Gemini", str(exc))
            return
        self.refresh()

    @Slot()
    def import_keys(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self._page,
            "Import API Gemini dari TXT",
            "",
            "Text files (*.txt);;All files (*)",
        )
        if not filename:
            return
        try:
            lines = tuple(Path(filename).read_text(encoding="utf-8-sig").splitlines())
            created = self._registry.import_keys(lines)
        except (OSError, UnicodeError, ValueError, CredentialStorageError) as exc:
            QMessageBox.warning(self._page, "API Gemini", str(exc))
            return
        self.refresh()
        QMessageBox.information(
            self._page,
            "API Gemini",
            f"{len(created)} API key berhasil disimpan dengan aman.",
        )

    @Slot()
    def test_active_key(self) -> None:
        try:
            active_profile = self._registry.active_profile()
        except CredentialStorageError:
            QMessageBox.warning(
                self._page,
                "API Gemini",
                "Penyimpanan aman Windows belum bisa diakses.",
            )
            return
        if active_profile is None:
            QMessageBox.information(
                self._page,
                "API Gemini",
                "Belum ada API key aktif yang tersimpan. Tambahkan key dulu.",
            )
            return

        self._page.test_button.setDisabled(True)
        task = _CheckTask(self._provider.check)

        def finished(raw: object) -> None:
            try:
                self._handle_check(cast(_CheckResult, raw))
            finally:
                self._tasks.discard(task)

        task.signals.finished.connect(finished)
        self._tasks.add(task)
        self._thread_pool.start(task)

    def _handle_check(self, result: _CheckResult) -> None:
        self._page.test_button.setDisabled(False)
        if result.error is None:
            try:
                self._registry.mark_active_status("Aktif")
            except CredentialStorageError:
                self.refresh()
                QMessageBox.warning(
                    self._page,
                    "API Gemini",
                    "API key bisa dipakai, tetapi statusnya tidak dapat disimpan.",
                )
                return
            self.refresh()
            QMessageBox.information(self._page, "API Gemini", "API key aktif dan bisa digunakan.")
            return

        status = "Error"
        message = "API key belum bisa digunakan."
        if isinstance(result.error, AIProviderError):
            if result.error.error_code == "invalid_api_key":
                status = "Tidak valid"
                message = "API key ditolak oleh Gemini."
            elif result.error.error_code == "rate_limited":
                status = "Rate Limit"
                message = "API key sedang terkena batas pemakaian."
            elif result.error.error_code == "network_error":
                status = "Gangguan jaringan"
                message = "Gemini belum bisa dihubungi dari koneksi ini."
        with suppress(CredentialStorageError):
            self._registry.mark_active_status(status)
        self.refresh()
        QMessageBox.warning(self._page, "API Gemini", message)
