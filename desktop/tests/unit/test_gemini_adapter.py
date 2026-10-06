from __future__ import annotations

from types import SimpleNamespace
from typing import ClassVar

import pytest

import metube_srt_desktop.adapters.ai.gemini as gemini_module
from metube_srt_desktop.adapters.ai.gemini import GeminiAdapter
from metube_srt_desktop.application.dto.ai_chat import AIChatMessage, AIChatRole


class FakeAPIError(Exception):
    def __init__(self, code: int) -> None:
        super().__init__("provider rejected key")
        self.code = code


class FakeModels:
    def __init__(self, api_key: str, calls: list[str]) -> None:
        self._api_key = api_key
        self._calls = calls

    def generate_content(self, **kwargs: object) -> object:
        self._calls.append(self._api_key)
        if self._api_key == "bad-key":
            raise FakeAPIError(401)
        return SimpleNamespace(text="Siap, key kedua berhasil.")


class FakeClient:
    calls: ClassVar[list[str]] = []

    def __init__(self, *, api_key: str) -> None:
        self.models = FakeModels(api_key, type(self).calls)

    def close(self) -> None:
        return


def test_generate_reply_fails_over_only_after_invalid_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gemini_module.errors, "APIError", FakeAPIError)
    monkeypatch.setattr(gemini_module.genai, "Client", FakeClient)
    FakeClient.calls.clear()

    keys = ["bad-key", "good-key"]

    def key_source() -> str | None:
        return keys[0] if keys else None

    def mark_invalid() -> None:
        keys.pop(0)

    adapter = GeminiAdapter(
        key_source,
        invalid_key_handler=mark_invalid,
    )

    reply = adapter.generate_reply(
        system_instruction="Balas singkat.",
        messages=(AIChatMessage(AIChatRole.USER, "halo"),),
    )

    assert reply == "Siap, key kedua berhasil."
    assert FakeClient.calls == ["bad-key", "good-key"]
    assert keys == ["good-key"]


def test_generate_reply_does_not_rotate_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RateLimitedModels(FakeModels):
        def generate_content(self, **kwargs: object) -> object:
            self._calls.append(self._api_key)
            raise FakeAPIError(429)

    class RateLimitedClient(FakeClient):
        def __init__(self, *, api_key: str) -> None:
            self.models = RateLimitedModels(api_key, type(self).calls)

    monkeypatch.setattr(gemini_module.errors, "APIError", FakeAPIError)
    monkeypatch.setattr(gemini_module.genai, "Client", RateLimitedClient)
    RateLimitedClient.calls.clear()
    rotated = False

    def mark_invalid() -> None:
        nonlocal rotated
        rotated = True

    adapter = GeminiAdapter(lambda: "rate-limited-key", invalid_key_handler=mark_invalid)

    with pytest.raises(Exception) as caught:
        adapter.generate_reply(
            system_instruction="Balas singkat.",
            messages=(AIChatMessage(AIChatRole.USER, "halo"),),
        )

    assert getattr(caught.value, "error_code", None) == "rate_limited"
    assert rotated is False
    assert RateLimitedClient.calls == ["rate-limited-key"]
