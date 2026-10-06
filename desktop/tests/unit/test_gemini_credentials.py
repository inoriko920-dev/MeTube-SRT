from __future__ import annotations

from metube_srt_desktop.application.dto.gemini_credentials import GeminiKeyProfile
from metube_srt_desktop.application.gemini_credentials import GeminiCredentialRegistry


class MemoryProfiles:
    def __init__(self) -> None:
        self.items: dict[str, GeminiKeyProfile] = {}

    def list_profiles(self) -> tuple[GeminiKeyProfile, ...]:
        return tuple(sorted(self.items.values(), key=lambda item: item.priority))

    def save_profile(self, profile: GeminiKeyProfile) -> None:
        self.items[profile.profile_id] = profile

    def delete_profile(self, profile_id: str) -> None:
        self.items.pop(profile_id, None)


class MemorySecrets:
    def __init__(self) -> None:
        self.items: dict[str, str] = {}

    def set_secret(self, profile_id: str, secret: str) -> None:
        self.items[profile_id] = secret

    def get_secret(self, profile_id: str) -> str | None:
        return self.items.get(profile_id)

    def delete_secret(self, profile_id: str) -> None:
        self.items.pop(profile_id, None)


def test_registry_keeps_raw_key_out_of_profile_metadata() -> None:
    profiles = MemoryProfiles()
    secrets = MemorySecrets()
    registry = GeminiCredentialRegistry(profiles, secrets)
    raw_key = "AIzaSyExampleLongSecretKey123456789"

    profile = registry.add_profile("Utama", raw_key)

    assert profile.label == "Utama"
    assert registry.active_secret() == raw_key
    assert raw_key not in repr(profile)
    assert profiles.list_profiles()[0].status == "Belum diuji"


def test_import_keys_assigns_stable_priorities() -> None:
    profiles = MemoryProfiles()
    secrets = MemorySecrets()
    registry = GeminiCredentialRegistry(profiles, secrets)

    created = registry.import_keys(
        (
            "AIzaSyExampleLongSecretKey000000001",
            "AIzaSyExampleLongSecretKey000000002",
        )
    )

    assert [item.priority for item in created] == [1, 2]
    assert [item.label for item in created] == ["Gemini 01", "Gemini 02"]
    assert registry.active_secret() == "AIzaSyExampleLongSecretKey000000001"


def test_mark_active_status_updates_only_metadata() -> None:
    profiles = MemoryProfiles()
    secrets = MemorySecrets()
    registry = GeminiCredentialRegistry(profiles, secrets)
    raw_key = "AIzaSyExampleLongSecretKey000000003"
    registry.add_profile("Utama", raw_key)

    registry.mark_active_status("Aktif")

    profile = registry.active_profile()
    assert profile is not None
    assert profile.status == "Aktif"
    assert profile.last_tested_at is not None
    assert registry.active_secret() == raw_key
