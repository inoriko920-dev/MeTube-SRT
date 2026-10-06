from __future__ import annotations

import os
from collections.abc import Callable
from time import sleep
from contextlib import suppress
from typing import Protocol, cast

from google import genai
from google.genai import errors, types

from metube_srt_desktop.application.dto.ai_chat import AIChatMessage, AIChatRole
from metube_srt_desktop.application.ports.ai_provider import AIProviderError, AIProviderPort
from metube_srt_desktop.application.ports.credentials import (
    CredentialCooldownError,
    CredentialStorageError,
)

_DEFAULT_MODEL = "gemini-2.5-flash"
_GEMINI_REQUEST_TIMEOUT_MS = 30_000
_TRANSIENT_RETRY_DELAYS_SECONDS = (0.25, 0.75)


class _GenerateModels(Protocol):
    def generate_content(
        self,
        *,
        model: str,
        contents: object,
        config: types.GenerateContentConfig | None = None,
    ) -> types.GenerateContentResponse: ...


class GeminiAdapter(AIProviderPort):
    """Official google-genai adapter behind the application AI boundary."""

    def __init__(
        self,
        api_key_source: Callable[[], str | None],
        *,
        model: str | None = None,
        invalid_key_handler: Callable[[], None] | None = None,
        rate_limit_handler: Callable[[], None] | None = None,
        sleep_fn: Callable[[float], None] = sleep,
    ) -> None:
        self._api_key_source = api_key_source
        self._invalid_key_handler = invalid_key_handler
        self._rate_limit_handler = rate_limit_handler
        self._sleep = sleep_fn
        self._model = (model or os.environ.get("METUBE_SRT_GEMINI_MODEL") or _DEFAULT_MODEL).strip()
        if not self._model:
            raise ValueError("Gemini model must be non-empty")

    @property
    def model(self) -> str:
        return self._model

    def generate_reply(
        self,
        *,
        system_instruction: str,
        messages: tuple[AIChatMessage, ...],
    ) -> str:
        contents = [_to_content(message) for message in messages]
        api_key = self._require_api_key()

        for _ in range(100):
            try:
                return self._generate_with_retries(
                    api_key,
                    system_instruction=system_instruction,
                    contents=contents,
                )
            except AIProviderError as exc:
                if exc.error_code == "rate_limited":
                    self._mark_rate_limited()
                    raise
                if exc.error_code != "invalid_api_key":
                    raise
                next_key = self._next_key_after_invalid(api_key)
                if next_key is None:
                    raise
                api_key = next_key

        raise AIProviderError("invalid_api_key", "Semua API key Gemini aktif ditolak.")

    def _generate_with_retries(
        self,
        api_key: str,
        *,
        system_instruction: str,
        contents: list[types.Content],
    ) -> str:
        for retry_index in range(len(_TRANSIENT_RETRY_DELAYS_SECONDS) + 1):
            try:
                return self._generate_with_key(
                    api_key,
                    system_instruction=system_instruction,
                    contents=contents,
                )
            except AIProviderError as exc:
                if exc.error_code != "network_error" or retry_index >= len(
                    _TRANSIENT_RETRY_DELAYS_SECONDS
                ):
                    raise
                self._sleep(_TRANSIENT_RETRY_DELAYS_SECONDS[retry_index])
        raise AIProviderError("network_error", "Gemini sedang tidak tersedia.")

    def _generate_with_key(
        self,
        api_key: str,
        *,
        system_instruction: str,
        contents: list[types.Content],
    ) -> str:
        client: genai.Client | None = None
        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=_GEMINI_REQUEST_TIMEOUT_MS),
            )
            models = cast(_GenerateModels, client.models)
            response = models.generate_content(
                model=self._model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.65,
                    max_output_tokens=700,
                ),
            )
        except errors.APIError as exc:
            raise _map_api_error(exc) from exc
        except (OSError, TimeoutError) as exc:
            raise AIProviderError(
                "network_error",
                "Gemini tidak dapat dijangkau.",
            ) from exc
        except Exception as exc:
            raise AIProviderError(
                "provider_error",
                "Gemini tidak dapat memproses permintaan.",
            ) from exc
        finally:
            if client is not None:
                with suppress(Exception):
                    client.close()

        text = response.text
        if text is None or not text.strip():
            raise AIProviderError("empty_response", "Gemini tidak mengembalikan jawaban.")
        return text.strip()

    def _next_key_after_invalid(self, previous_key: str) -> str | None:
        if self._invalid_key_handler is None:
            return None
        try:
            self._invalid_key_handler()
        except CredentialStorageError as exc:
            raise AIProviderError(
                "credential_storage_error",
                "Status API key tidak dapat diperbarui.",
            ) from exc

        try:
            candidate = self._api_key_source()
        except CredentialStorageError as exc:
            raise AIProviderError(
                "credential_storage_error",
                "Penyimpanan aman API key tidak dapat diakses.",
            ) from exc
        if candidate is None:
            return None
        clean = candidate.strip()
        if not clean or clean == previous_key:
            return None
        return clean

    def check(self) -> None:
        api_key = self._require_api_key()
        try:
            self._check_with_retries(api_key)
        except AIProviderError as exc:
            if exc.error_code == "rate_limited":
                self._mark_rate_limited()
            raise

    def _check_with_retries(self, api_key: str) -> None:
        for retry_index in range(len(_TRANSIENT_RETRY_DELAYS_SECONDS) + 1):
            try:
                self._check_with_key(api_key)
                return
            except AIProviderError as exc:
                if (
                    exc.error_code != "network_error"
                    or retry_index >= len(_TRANSIENT_RETRY_DELAYS_SECONDS)
                ):
                    raise
                self._sleep(_TRANSIENT_RETRY_DELAYS_SECONDS[retry_index])

    def _check_with_key(self, api_key: str) -> None:
        client: genai.Client | None = None
        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=_GEMINI_REQUEST_TIMEOUT_MS),
            )
            models = cast(_GenerateModels, client.models)
            response = models.generate_content(
                model=self._model,
                contents="Balas hanya dengan kata OK.",
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=8,
                ),
            )
        except errors.APIError as exc:
            raise _map_api_error(exc) from exc
        except (OSError, TimeoutError) as exc:
            raise AIProviderError("network_error", "Gemini tidak dapat dijangkau.") from exc
        except Exception as exc:
            raise AIProviderError("provider_error", "Gemini tidak dapat diuji.") from exc
        finally:
            if client is not None:
                with suppress(Exception):
                    client.close()

        if response.text is None or not response.text.strip():
            raise AIProviderError("empty_response", "Gemini tidak mengembalikan jawaban.")

    def _mark_rate_limited(self) -> None:
        if self._rate_limit_handler is None:
            return
        try:
            self._rate_limit_handler()
        except CredentialStorageError as exc:
            raise AIProviderError(
                "credential_storage_error",
                "Cooldown API key tidak dapat disimpan.",
            ) from exc

    def _require_api_key(self) -> str:
        try:
            api_key = self._api_key_source()
        except CredentialCooldownError as exc:
            raise AIProviderError(
                "rate_limited",
                f"API key Gemini sedang cooldown sekitar {exc.retry_after_seconds} detik.",
            ) from exc
        except CredentialStorageError as exc:
            raise AIProviderError(
                "credential_storage_error",
                "Penyimpanan aman API key tidak dapat diakses.",
            ) from exc
        if api_key is None or not api_key.strip():
            raise AIProviderError(
                "missing_api_key",
                "Belum ada API key Gemini aktif.",
            )
        return api_key.strip()


def _to_content(message: AIChatMessage) -> types.Content:
    role = "user" if message.role is AIChatRole.USER else "model"
    return types.Content(
        role=role,
        parts=[types.Part(text=message.text)],
    )


def _map_api_error(error: errors.APIError) -> AIProviderError:
    try:
        code = int(error.code)
    except (TypeError, ValueError):
        code = 0
    if code == 401:
        return AIProviderError("invalid_api_key", "API key Gemini ditolak.")
    if code == 403:
        return AIProviderError(
            "permission_denied",
            "Gemini menolak izin untuk model atau project ini.",
        )
    if code == 429:
        return AIProviderError("rate_limited", "Batas pemakaian Gemini tercapai.")
    if code in {408, 500, 502, 503, 504}:
        return AIProviderError("network_error", "Gemini sedang tidak tersedia.")
    return AIProviderError("provider_error", "Gemini tidak dapat memproses permintaan.")
