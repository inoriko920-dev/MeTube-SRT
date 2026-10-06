from __future__ import annotations

from typing import Protocol, runtime_checkable

from metube_srt_desktop.application.dto.ai_chat import AIChatMessage


class AIProviderError(RuntimeError):
    """Sanitized application-owned AI provider failure."""

    def __init__(self, error_code: str, message: str) -> None:
        if not error_code.strip():
            raise ValueError("error_code must be non-empty")
        if not message.strip():
            raise ValueError("message must be non-empty")
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class AIProviderPort(Protocol):
    def generate_reply(
        self,
        *,
        system_instruction: str,
        messages: tuple[AIChatMessage, ...],
    ) -> str: ...

    def check(self) -> None: ...


@runtime_checkable
class AIProviderProfileCheckPort(Protocol):
    def check_profile(self, profile_id: str) -> None: ...


@runtime_checkable
class AIProviderCancellationPort(Protocol):
    def cancel_current(self) -> None: ...
