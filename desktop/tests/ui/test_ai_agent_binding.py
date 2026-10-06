from __future__ import annotations

from collections.abc import Iterable

from pytestqt.qtbot import QtBot

from metube_srt_desktop.application.ai_conversation import HumanlikeAIConversation
from metube_srt_desktop.application.download_queue import BoundedDownloadQueue
from metube_srt_desktop.application.dto.ai_chat import AIChatMessage
from metube_srt_desktop.application.dto.download import ResolvedSource, ResolveRequest
from metube_srt_desktop.application.dto.worker_protocol import WorkerEnvelope
from metube_srt_desktop.application.ports.download_worker import DownloadWorkerPort
from metube_srt_desktop.domain.jobs import JobSpec
from metube_srt_desktop.presentation.shell.main_window import MainWindow


class HumanProvider:
    def generate_reply(
        self,
        *,
        system_instruction: str,
        messages: tuple[AIChatMessage, ...],
    ) -> str:
        return "Siap. Saya ingat konteksnya dan akan bantu tanpa mengulang pertanyaan."

    def check(self) -> None:
        return


class UnusedResolver:
    def resolve(self, request: ResolveRequest) -> ResolvedSource:
        raise AssertionError("resolver must not be called by AI chat binding test")


class NoopWorker:
    def events(self) -> Iterable[WorkerEnvelope]:
        return ()

    def request_cancel(self) -> None:
        return


class NoopWorkerFactory:
    def create(
        self,
        job: JobSpec,
        *,
        worker_run_id: str,
    ) -> DownloadWorkerPort:
        return NoopWorker()


def test_ai_panel_sends_message_and_renders_human_reply(qtbot: QtBot) -> None:
    queue = BoundedDownloadQueue(NoopWorkerFactory())
    conversation = HumanlikeAIConversation(HumanProvider())
    window = MainWindow(
        queue=queue,
        resolver=UnusedResolver(),
        ai_conversation=conversation,
    )
    qtbot.addWidget(window)
    window.show()

    try:
        window.ai_workspace.prompt.setPlainText("yang tadi ulang lagi")
        window.ai_workspace.send_button.click()

        qtbot.waitUntil(
            lambda: "Saya ingat konteksnya" in window.ai_workspace.transcript.toPlainText(),
            timeout=2000,
        )

        transcript = window.ai_workspace.transcript.toPlainText()
        assert "yang tadi ulang lagi" in transcript
        assert "Siap." in transcript
        assert window.ai_workspace.status_label.text() == "Siap"
    finally:
        queue.shutdown(wait=True)
