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
    def __init__(self, credential: str, calls: list[str]) -> None:
        self._credential = credential
        self._calls = calls

    def generate_content(self, **kwargs: object) -> object:
        self._calls.append(self._credential)
        if self._credential == "bad-key":
            raise FakeAPIError(401)
        return SimpleNamespace(text="Siap, key kedua berhasil.")


class FakeClient:
    calls: ClassVar[list[str]] = []
    timeouts: ClassVar[list[object]] = []

    def __init__(self, *, api_key: str, http_options: object | None = None) -> None:
        self.models = FakeModels(api_key, type(self).calls)
        type(self).timeouts.append(getattr(http_options, "timeout", None))

    def close(self) -> None:
        return


def test_generate_reply_fails_over_only_after_invalid_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gemini_module.errors, "APIError", FakeAPIError)
    monkeypatch.setattr(gemini_module.genai, "Client", FakeClient)
    FakeClient.calls.clear()
    FakeClient.timeouts.clear()

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
    assert FakeClient.timeouts == [30_000, 30_000]
    assert keys == ["good-key"]


def test_generate_reply_does_not_rotate_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RateLimitedModels(FakeModels):
        def generate_content(self, **kwargs: object) -> object:
            self._calls.append(self._credential)
            raise FakeAPIError(429)

    class RateLimitedClient(FakeClient):
        def __init__(self, *, api_key: str, http_options: object | None = None) -> None:
            self.models = RateLimitedModels(api_key, type(self).calls)
            type(self).timeouts.append(getattr(http_options, "timeout", None))

    monkeypatch.setattr(gemini_module.errors, "APIError", FakeAPIError)
    monkeypatch.setattr(gemini_module.genai, "Client", RateLimitedClient)
    RateLimitedClient.calls.clear()
    RateLimitedClient.timeouts.clear()
    invalidated = False
    cooled_down = False

    def mark_invalid() -> None:
        nonlocal invalidated
        invalidated = True

    def mark_cooldown() -> None:
        nonlocal cooled_down
        cooled_down = True

    adapter = GeminiAdapter(
        lambda: "rate-limited-key",
        invalid_key_handler=mark_invalid,
        rate_limit_handler=mark_cooldown,
    )

    with pytest.raises(Exception) as caught:
        adapter.generate_reply(
            system_instruction="Balas singkat.",
            messages=(AIChatMessage(AIChatRole.USER, "halo"),),
        )

    assert getattr(caught.value, "error_code", None) == "rate_limited"
    assert invalidated is False
    assert cooled_down is True
    assert RateLimitedClient.calls == ["rate-limited-key"]
    assert RateLimitedClient.timeouts == [30_000]


def test_generate_reply_does_not_invalidate_key_on_permission_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class PermissionDeniedModels(FakeModels):
        def generate_content(self, **kwargs: object) -> object:
            self._calls.append(self._credential)
            raise FakeAPIError(403)

    class PermissionDeniedClient(FakeClient):
        def __init__(self, *, api_key: str, http_options: object | None = None) -> None:
            self.models = PermissionDeniedModels(api_key, type(self).calls)
            type(self).timeouts.append(getattr(http_options, "timeout", None))

    monkeypatch.setattr(gemini_module.errors, "APIError", FakeAPIError)
    monkeypatch.setattr(gemini_module.genai, "Client", PermissionDeniedClient)
    PermissionDeniedClient.calls.clear()
    PermissionDeniedClient.timeouts.clear()
    invalidated = False

    def mark_invalid() -> None:
        nonlocal invalidated
        invalidated = True

    adapter = GeminiAdapter(
        lambda: "permission-denied-key",
        invalid_key_handler=mark_invalid,
    )

    with pytest.raises(Exception) as caught:
        adapter.generate_reply(
            system_instruction="Balas singkat.",
            messages=(AIChatMessage(AIChatRole.USER, "halo"),),
        )

    assert getattr(caught.value, "error_code", None) == "permission_denied"
    assert invalidated is False
    assert PermissionDeniedClient.calls == ["permission-denied-key"]


def test_generate_reply_maps_registry_cooldown_without_provider_call() -> None:
    from metube_srt_desktop.application.ports.credentials import CredentialCooldownError

    calls = 0

    def key_source() -> str | None:
        nonlocal calls
        calls += 1
        raise CredentialCooldownError(42)

    adapter = GeminiAdapter(key_source)

    with pytest.raises(Exception) as caught:
        adapter.generate_reply(
            system_instruction="Balas singkat.",
            messages=(AIChatMessage(AIChatRole.USER, "halo"),),
        )

    assert getattr(caught.value, "error_code", None) == "rate_limited"
    assert "42 detik" in str(caught.value)
    assert calls == 1



def test_generate_reply_retries_transient_503_on_same_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FlakyModels(FakeModels):
        attempts: ClassVar[int] = 0

        def generate_content(self, **kwargs: object) -> object:
            self._calls.append(self._credential)
            type(self).attempts += 1
            if type(self).attempts < 3:
                raise FakeAPIError(503)
            return SimpleNamespace(text="Pulih setelah gangguan sementara.")

    class FlakyClient(FakeClient):
        def __init__(self, *, api_key: str, http_options: object | None = None) -> None:
            self.models = FlakyModels(api_key, type(self).calls)
            type(self).timeouts.append(getattr(http_options, "timeout", None))

    monkeypatch.setattr(gemini_module.errors, "APIError", FakeAPIError)
    monkeypatch.setattr(gemini_module.genai, "Client", FlakyClient)
    FlakyClient.calls.clear()
    FlakyClient.timeouts.clear()
    FlakyModels.attempts = 0
    delays: list[float] = []

    adapter = GeminiAdapter(
        lambda: "same-key",
        sleep_fn=delays.append,
    )

    reply = adapter.generate_reply(
        system_instruction="Balas singkat.",
        messages=(AIChatMessage(AIChatRole.USER, "halo"),),
    )

    assert reply == "Pulih setelah gangguan sementara."
    assert FlakyClient.calls == ["same-key", "same-key", "same-key"]
    assert delays == [0.25, 0.75]


def test_generate_reply_stops_after_transient_retry_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DownModels(FakeModels):
        def generate_content(self, **kwargs: object) -> object:
            self._calls.append(self._credential)
            raise FakeAPIError(503)

    class DownClient(FakeClient):
        def __init__(self, *, api_key: str, http_options: object | None = None) -> None:
            self.models = DownModels(api_key, type(self).calls)
            type(self).timeouts.append(getattr(http_options, "timeout", None))

    monkeypatch.setattr(gemini_module.errors, "APIError", FakeAPIError)
    monkeypatch.setattr(gemini_module.genai, "Client", DownClient)
    DownClient.calls.clear()
    DownClient.timeouts.clear()
    delays: list[float] = []

    adapter = GeminiAdapter(
        lambda: "same-key",
        sleep_fn=delays.append,
    )

    with pytest.raises(Exception) as caught:
        adapter.generate_reply(
            system_instruction="Balas singkat.",
            messages=(AIChatMessage(AIChatRole.USER, "halo"),),
        )

    assert getattr(caught.value, "error_code", None) == "network_error"
    assert DownClient.calls == ["same-key", "same-key", "same-key"]
    assert delays == [0.25, 0.75]
