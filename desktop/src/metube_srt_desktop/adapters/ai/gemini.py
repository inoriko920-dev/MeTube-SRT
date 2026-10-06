from __future__ import annotations

import os
from collections.abc import Callable
from contextlib import suppress
from typing import Protocol, cast

from google import genai
from google.genai import errors, types

from metube_srt_desktop.application.dto.ai_chat import AIChatMessage, AIChatRole
from metube_srt_desktop.application.ports.ai_provider import AIProviderError, AIProviderPort
from metube_srt_desktop.application.ports.credentials import CredentialStorageError

_DEFAULT_MODEL = "gemini-2.5-flash"
_GEMINI_REQUEST_TIMEOUT_MS = 30_000


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
    ) -> None:
        self._api_key_source = api_key_source
        self._invalid_key_handler = invalid_key_handler
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
                return self._generate_with_key(
                    api_key,
                    system_instruction=system_instruction,
                    contents=contents,
                )
            except AIProviderError as exc:
                if exc.error_code != "invalid_api_key":
                    raise
                next_key = self._next_key_after_invalid(api_key)
                if next_key is None:
                    raise
                api_key = next_key

        raise AIProviderError("invalid_api_key", "Semua API key Gemini aktif ditolak.")

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

    def _require_api_key(self) -> str:
        try:
            api_key = self._api_key_source()
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
    if code in {401, 403}:
        return AIProviderError("invalid_api_key", "API key Gemini ditolak.")
    if code == 429:
        return AIProviderError("rate_limited", "Batas pemakaian Gemini tercapai.")
    if code in {408, 500, 502, 503, 504}:
        return AIProviderError("network_error", "Gemini sedang tidak tersedia.")
    return AIProviderError("provider_error", "Gemini tidak dapat memproses permintaan.")
