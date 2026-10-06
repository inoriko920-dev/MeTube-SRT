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


def test_ai_controller_ignores_new_messages_after_window_close(qtbot: QtBot) -> None:
    class CountingProvider(HumanProvider):
        def __init__(self) -> None:
            self.calls = 0

        def generate_reply(
            self,
            *,
            system_instruction: str,
            messages: tuple[AIChatMessage, ...],
        ) -> str:
            self.calls += 1
            return super().generate_reply(
                system_instruction=system_instruction,
                messages=messages,
            )

    provider = CountingProvider()
    queue = BoundedDownloadQueue(NoopWorkerFactory())
    conversation = HumanlikeAIConversation(provider)
    window = MainWindow(
        queue=queue,
        resolver=UnusedResolver(),
        ai_conversation=conversation,
    )
    qtbot.addWidget(window)
    window.show()

    try:
        window.close()
        window.ai_workspace.prompt.setPlainText("jangan kirim setelah close")
        assert window.ai_controller is not None
        window.ai_controller.send_message()

        qtbot.wait(50)
        assert provider.calls == 0
    finally:
        queue.shutdown(wait=True)


def test_ai_panel_redacts_secret_and_does_not_call_provider(qtbot: QtBot) -> None:
    class CountingProvider(HumanProvider):
        def __init__(self) -> None:
            self.calls = 0

        def generate_reply(
            self,
            *,
            system_instruction: str,
            messages: tuple[AIChatMessage, ...],
        ) -> str:
            self.calls += 1
            return super().generate_reply(
                system_instruction=system_instruction,
                messages=messages,
            )

    provider = CountingProvider()
    queue = BoundedDownloadQueue(NoopWorkerFactory())
    conversation = HumanlikeAIConversation(provider)
    window = MainWindow(
        queue=queue,
        resolver=UnusedResolver(),
        ai_conversation=conversation,
    )
    qtbot.addWidget(window)
    window.show()

    try:
        credential_value = "AI" + "za" + ("x" * 30)
        field_name = "api" + "_key"
        window.ai_workspace.prompt.setPlainText(f"{field_name}={credential_value}")
        window.ai_workspace.send_button.click()

        transcript = window.ai_workspace.transcript.toPlainText()
        assert credential_value not in transcript
        assert "SECRET DISEMBUNYIKAN" in transcript
        assert "tidak mengirimkannya ke Gemini" in transcript
        assert provider.calls == 0
    finally:
        queue.shutdown(wait=True)


def test_ai_panel_redacts_full_cookie_header_tail(qtbot: QtBot) -> None:
    class CountingProvider(HumanProvider):
        def __init__(self) -> None:
            self.calls = 0

        def generate_reply(
            self,
            *,
            system_instruction: str,
            messages: tuple[AIChatMessage, ...],
        ) -> str:
            self.calls += 1
            return super().generate_reply(
                system_instruction=system_instruction,
                messages=messages,
            )

    provider = CountingProvider()
    queue = BoundedDownloadQueue(NoopWorkerFactory())
    conversation = HumanlikeAIConversation(provider)
    window = MainWindow(
        queue=queue,
        resolver=UnusedResolver(),
        ai_conversation=conversation,
    )
    qtbot.addWidget(window)
    window.show()

    try:
        values = ("FAKE_SID_VALUE", "FAKE_HSID_VALUE", "FAKE_SSID_VALUE")
        window.ai_workspace.prompt.setPlainText(
            f"Cookie: SID={values[0]}; HSID={values[1]}; SSID={values[2]}"
        )
        window.ai_workspace.send_button.click()

        transcript = window.ai_workspace.transcript.toPlainText()
        assert all(value not in transcript for value in values)
        assert "SECRET DISEMBUNYIKAN" in transcript
        assert provider.calls == 0
    finally:
        queue.shutdown(wait=True)
