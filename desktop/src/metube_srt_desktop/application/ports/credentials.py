from __future__ import annotations

from typing import Protocol

from metube_srt_desktop.application.dto.gemini_credentials import GeminiKeyProfile


class CredentialStorageError(RuntimeError):
    """Application-owned credential storage failure."""


class CredentialCooldownError(RuntimeError):
    """The selected Gemini credential is intentionally cooling down."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Gemini credential is cooling down")
        self.retry_after_seconds = max(1, retry_after_seconds)


class CredentialSecretPort(Protocol):
    def set_secret(self, profile_id: str, secret: str) -> None: ...

    def get_secret(self, profile_id: str) -> str | None: ...

    def delete_secret(self, profile_id: str) -> None: ...


class GeminiProfileRepositoryPort(Protocol):
    def list_profiles(self) -> tuple[GeminiKeyProfile, ...]: ...

    def save_profile(self, profile: GeminiKeyProfile) -> None: ...

    def delete_profile(self, profile_id: str) -> None: ...
