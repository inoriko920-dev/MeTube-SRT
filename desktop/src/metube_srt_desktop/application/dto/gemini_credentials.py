from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeminiKeyProfile:
    profile_id: str
    label: str
    enabled: bool
    priority: int
    status: str = "Belum diuji"
    last_tested_at: str | None = None
    cooldown_until: str | None = None
    secret_available: bool | None = None

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("profile_id must be non-empty")
        if not self.label.strip():
            raise ValueError("label must be non-empty")
        if self.priority < 1:
            raise ValueError("priority must be >= 1")
        if not self.status.strip():
            raise ValueError("status must be non-empty")
