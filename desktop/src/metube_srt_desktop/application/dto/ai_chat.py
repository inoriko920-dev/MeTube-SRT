from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AIChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class AIChatMessage:
    role: AIChatRole
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("AI chat message must be non-empty")


@dataclass(frozen=True, slots=True)
class AIAgentContext:
    current_url: str | None = None
    quality: str | None = None
    subtitle_requested: bool = False
    output_directory: str | None = None
    queue_active: int = 0
    queue_waiting: int = 0
    queue_failed: int = 0

    def __post_init__(self) -> None:
        for value in (self.queue_active, self.queue_waiting, self.queue_failed):
            if value < 0:
                raise ValueError("queue counters must be non-negative")


@dataclass(frozen=True, slots=True)
class AIConversationReply:
    text: str
    provider_ok: bool
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("AI reply must be non-empty")
        if self.provider_ok and self.error_code is not None:
            raise ValueError("successful AI reply cannot carry an error code")
