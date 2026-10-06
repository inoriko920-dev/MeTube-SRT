from __future__ import annotations

from metube_srt_desktop.application.ai_conversation import HumanlikeAIConversation
from metube_srt_desktop.application.dto.ai_chat import AIAgentContext, AIChatMessage, AIChatRole
from metube_srt_desktop.application.ports.ai_provider import AIProviderError
from metube_srt_desktop.application.redaction import redact_sensitive_text


class FakeProvider:
    def __init__(self, replies: tuple[str, ...] = ("Siap, saya ikuti konteksnya.",)) -> None:
        self._replies = iter(replies)
        self.calls: list[tuple[str, tuple[AIChatMessage, ...]]] = []

    def generate_reply(
        self,
        *,
        system_instruction: str,
        messages: tuple[AIChatMessage, ...],
    ) -> str:
        self.calls.append((system_instruction, messages))
        return next(self._replies)

    def check(self) -> None:
        return


class MissingKeyProvider:
    def generate_reply(
        self,
        *,
        system_instruction: str,
        messages: tuple[AIChatMessage, ...],
    ) -> str:
        raise AIProviderError("missing_api_key", "missing")

    def check(self) -> None:
        raise AIProviderError("missing_api_key", "missing")


def test_humanlike_conversation_includes_style_policy_and_app_context() -> None:
    provider = FakeProvider()
    conversation = HumanlikeAIConversation(provider)
    context = AIAgentContext(
        current_url="https://www.youtube.com/watch?v=abc",
        quality="720p",
        subtitle_requested=False,
        output_directory="D:/Video",
        queue_active=1,
        queue_waiting=2,
    )

    reply = conversation.reply("yang tadi ulang lagi", context)

    assert reply.provider_ok is True
    system, messages = provider.calls[0]
    assert "Bahasa Indonesia yang alami" in system
    assert "jangan bertanya ulang" in system.lower()
    assert "yang tadi" in system
    assert "Kualitas: 720p" in messages[-2].text
    assert messages[-1] == AIChatMessage(AIChatRole.USER, "yang tadi ulang lagi")


def test_conversation_remembers_real_turns_without_storing_context_messages() -> None:
    provider = FakeProvider(("Baik, yang pertama saya ingat.", "Siap, saya lanjutkan."))
    conversation = HumanlikeAIConversation(provider)
    context = AIAgentContext(current_url="https://www.youtube.com/watch?v=abc")

    conversation.reply("download ini", context)
    conversation.reply("yang tadi tanpa subtitle", context)

    history = conversation.history()
    assert [message.role for message in history] == [
        AIChatRole.USER,
        AIChatRole.ASSISTANT,
        AIChatRole.USER,
        AIChatRole.ASSISTANT,
    ]
    assert history[0].text == "download ini"
    second_call_messages = provider.calls[1][1]
    assert any(message.text == "download ini" for message in second_call_messages)
    assert any(message.text == "yang tadi tanpa subtitle" for message in second_call_messages)


def test_missing_key_returns_friendly_human_response() -> None:
    conversation = HumanlikeAIConversation(MissingKeyProvider())

    reply = conversation.reply("halo", AIAgentContext())

    assert reply.provider_ok is False
    assert reply.error_code == "missing_api_key"
    assert "API Gemini belum ditambahkan" in reply.text
    assert "menu API Gemini" in reply.text


def test_secret_like_message_is_blocked_before_provider_call() -> None:
    provider = FakeProvider()
    conversation = HumanlikeAIConversation(provider)
    credential_value = "AI" + "za" + ("x" * 30)
    field_name = "api" + "_key"

    reply = conversation.reply(f"{field_name}={credential_value}", AIAgentContext())

    assert reply.provider_ok is False
    assert reply.error_code == "secret_blocked"
    assert provider.calls == []
    assert credential_value not in " ".join(message.text for message in conversation.history())
    assert "SECRET DISEMBUNYIKAN" in conversation.history()[0].text


def test_sensitive_download_context_is_redacted_before_provider_call() -> None:
    provider = FakeProvider()
    conversation = HumanlikeAIConversation(provider)
    account_name = "user"
    credential_value = "pass" + "-value"
    context = AIAgentContext(
        current_url=(f"https://{account_name}:{credential_value}@www.youtube.com/watch?v=abc"),
        output_directory="D:/Video",
    )

    reply = conversation.reply("kenapa belum mulai?", context)

    assert reply.provider_ok is True
    _, messages = provider.calls[0]
    serialized = "\n".join(message.text for message in messages)
    assert account_name not in serialized
    assert credential_value not in serialized
    assert "SECRET DISEMBUNYIKAN" in serialized


def test_named_api_key_redaction_produces_one_clean_marker() -> None:
    field_name = "api" + "_key"
    credential_value = "AI" + "za" + ("z" * 30)

    result = redact_sensitive_text(f"{field_name}={credential_value}")

    assert result.secret_detected is True
    assert result.text == f"{field_name}=[SECRET DISEMBUNYIKAN]"
    assert credential_value not in result.text


def test_named_bearer_redaction_does_not_leave_token_tail() -> None:
    field_name = "author" + "ization"
    credential_value = "Bearer " + ("t" * 24)

    result = redact_sensitive_text(f"{field_name}={credential_value}")

    assert result.secret_detected is True
    assert result.text == f"{field_name}=[SECRET DISEMBUNYIKAN]"
    assert credential_value not in result.text



def test_conversation_delegates_provider_cancellation() -> None:
    class CancellableProvider(FakeProvider):
        def __init__(self) -> None:
            super().__init__()
            self.cancelled = False

        def cancel_current(self) -> None:
            self.cancelled = True

    provider = CancellableProvider()
    conversation = HumanlikeAIConversation(provider)

    conversation.cancel_current()

    assert provider.cancelled is True
