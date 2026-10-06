from __future__ import annotations

import keyring
from keyring.errors import KeyringError, PasswordDeleteError

from metube_srt_desktop.application.ports.credentials import (
    CredentialSecretPort,
    CredentialStorageError,
)

_SERVICE_NAME = "MeTube-SRT/Gemini"


class KeyringGeminiSecretStore(CredentialSecretPort):
    """Store raw Gemini keys only in the operating-system credential backend."""

    def set_secret(self, profile_id: str, secret: str) -> None:
        try:
            keyring.set_password(_SERVICE_NAME, profile_id, secret)
        except KeyringError as exc:
            raise CredentialStorageError("API key tidak dapat disimpan dengan aman.") from exc

    def get_secret(self, profile_id: str) -> str | None:
        try:
            return keyring.get_password(_SERVICE_NAME, profile_id)
        except KeyringError as exc:
            raise CredentialStorageError(
                "API key tidak dapat dibaca dari penyimpanan aman."
            ) from exc

    def delete_secret(self, profile_id: str) -> None:
        try:
            keyring.delete_password(_SERVICE_NAME, profile_id)
        except PasswordDeleteError:
            return
        except KeyringError as exc:
            raise CredentialStorageError(
                "API key tidak dapat dihapus dari penyimpanan aman."
            ) from exc
