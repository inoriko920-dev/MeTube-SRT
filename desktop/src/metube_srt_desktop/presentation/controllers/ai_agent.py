from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from metube_srt_desktop.application.ai_conversation import HumanlikeAIConversation
from metube_srt_desktop.application.dto.ai_chat import AIAgentContext, AIConversationReply
from metube_srt_desktop.application.ports.download_queue import QueueRuntimePort
from metube_srt_desktop.domain.jobs import JobState
from metube_srt_desktop.presentation.components.ai_panel import AIWorkspace
from metube_srt_desktop.presentation.pages.download.page import DownloadPage


@dataclass(frozen=True, slots=True)
class _AIResult:
    reply: AIConversationReply | None
    error: Exception | None


class _AISignals(QObject):
    finished = Signal(object)


class _AITask(QRunnable):
    def __init__(self, call: Callable[[], AIConversationReply]) -> None:
        super().__init__()
        self._call = call
        self.signals = _AISignals()

    @Slot()
    def run(self) -> None:
        try:
            result = _AIResult(self._call(), None)
        except Exception as exc:
            result = _AIResult(None, exc)
        self.signals.finished.emit(result)


class AIAgentController(QObject):
    """Presentation binding for natural Gemini conversation."""

    def __init__(
        self,
        workspace: AIWorkspace,
        download_page: DownloadPage,
        queue: QueueRuntimePort,
        conversation: HumanlikeAIConversation,
        *,
        parent: QObject | None = None,
        thread_pool: QThreadPool | None = None,
    ) -> None:
        super().__init__(parent)
        self._workspace = workspace
        self._download_page = download_page
        self._queue = queue
        self._conversation = conversation
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._tasks: set[_AITask] = set()
        self._busy = False
        self._closed = False

        self._workspace.send_button.clicked.connect(self.send_message)
        self._workspace.append_assistant_message(
            "Halo. Bilang saja kamu ingin download apa atau tanyakan statusnya. "
            "Saya akan mengikuti konteks percakapan kita."
        )

    @Slot()
    def send_message(self) -> None:
        if self._closed or self._busy:
            return
        text = self._workspace.prompt.toPlainText().strip()
        if not text:
            return

        self._workspace.append_user_message(text)
        self._workspace.clear_prompt()
        self._busy = True
        self._workspace.set_busy(True)

        context = self._build_context()
        task = _AITask(lambda: self._conversation.reply(text, context))

        def finished(raw: object) -> None:
            try:
                if self._closed:
                    return
                self._handle_result(cast(_AIResult, raw))
            finally:
                self._tasks.discard(task)

        task.signals.finished.connect(finished)
        self._tasks.add(task)
        self._thread_pool.start(task)

    def _handle_result(self, result: _AIResult) -> None:
        self._busy = False
        self._workspace.set_busy(False)

        if result.reply is None:
            self._workspace.append_assistant_message(
                "Saya belum bisa memproses pesan itu sekarang. Coba kirim lagi sebentar."
            )
            self._workspace.set_status("Gangguan", success=False)
            return

        self._workspace.append_assistant_message(result.reply.text)
        if result.reply.provider_ok:
            self._workspace.set_status("Siap", success=True)
        elif result.reply.error_code == "missing_api_key":
            self._workspace.set_status("Butuh API", success=False)
        else:
            self._workspace.set_status("Gangguan", success=False)

    def _build_context(self) -> AIAgentContext:
        snapshots = self._queue.snapshots()
        active_states = {
            JobState.RESOLVING,
            JobState.RUNNING,
            JobState.POSTPROCESSING,
            JobState.CANCELLING,
        }
        failed_states = {JobState.FAILED, JobState.INTERRUPTED}
        return AIAgentContext(
            current_url=self._download_page.url_input.text().strip() or None,
            quality=self._download_page.quality_combo.currentText().strip() or None,
            subtitle_requested=self._download_page.subtitle_checkbox.isChecked(),
            output_directory=self._download_page.output_path.text().strip() or None,
            queue_active=sum(item.state in active_states for item in snapshots),
            queue_waiting=sum(item.state is JobState.QUEUED for item in snapshots),
            queue_failed=sum(item.state in failed_states for item in snapshots),
        )


    def shutdown(self) -> None:
        self._closed = True
