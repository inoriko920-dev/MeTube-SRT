from __future__ import annotations

import os
from collections.abc import Callable

from google import genai
from google.genai import errors, types

from metube_srt_desktop.application.dto.ai_chat import AIChatMessage, AIChatRole
from metube_srt_desktop.application.ports.ai_provider import AIProviderError, AIProviderPort

_DEFAULT_MODEL = "gemini-2.5-flash"


class GeminiAdapter(AIProviderPort):
    """Official google-genai adapter behind the application AI boundary."""

    def __init__(
        self,
        api_key_source: Callable[[], str | None],
        *,
        model: str | None = None,
    ) -> None:
        self._api_key_source = api_key_source
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
        api_key = self._require_api_key()
        contents = [_to_content(message) for message in messages]
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
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

        text = response.text
        if text is None or not text.strip():
            raise AIProviderError("empty_response", "Gemini tidak mengembalikan jawaban.")
        return text.strip()

    def check(self) -> None:
        api_key = self._require_api_key()
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
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

        if response.text is None or not response.text.strip():
            raise AIProviderError("empty_response", "Gemini tidak mengembalikan jawaban.")

    def _require_api_key(self) -> str:
        api_key = self._api_key_source()
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
    code = int(error.code)
    if code in {401, 403}:
        return AIProviderError("invalid_api_key", "API key Gemini ditolak.")
    if code == 429:
        return AIProviderError("rate_limited", "Batas pemakaian Gemini tercapai.")
    if code in {408, 500, 502, 503, 504}:
        return AIProviderError("network_error", "Gemini sedang tidak tersedia.")
    return AIProviderError("provider_error", "Gemini tidak dapat memproses permintaan.")
