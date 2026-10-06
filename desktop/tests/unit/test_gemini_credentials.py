from __future__ import annotations

from metube_srt_desktop.application.dto.gemini_credentials import GeminiKeyProfile
from metube_srt_desktop.application.gemini_credentials import GeminiCredentialRegistry
from metube_srt_desktop.application.ports.credentials import CredentialStorageError


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
    raw_key = "not-a-real-key-xxxxxxxxxxxxxxxxxxxxxxxx"

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
            "fake-key-one-xxxxxxxxxxxxxxxxxxxxxxxx",
            "fake-key-two-xxxxxxxxxxxxxxxxxxxxxxxx",
        )
    )

    assert [item.priority for item in created] == [1, 2]
    assert [item.label for item in created] == ["Gemini 01", "Gemini 02"]
    assert registry.active_secret() == "fake-key-one-xxxxxxxxxxxxxxxxxxxxxxxx"


def test_mark_active_status_updates_only_metadata() -> None:
    profiles = MemoryProfiles()
    secrets = MemorySecrets()
    registry = GeminiCredentialRegistry(profiles, secrets)
    raw_key = "fake-key-three-xxxxxxxxxxxxxxxxxxxxxx"
    registry.add_profile("Utama", raw_key)

    registry.mark_active_status("Aktif")

    profile = registry.active_profile()
    assert profile is not None
    assert profile.status == "Aktif"
    assert profile.last_tested_at is not None
    assert registry.active_secret() == raw_key


class FailingProfiles(MemoryProfiles):
    def __init__(self, fail_on_save_number: int) -> None:
        super().__init__()
        self._save_count = 0
        self._fail_on_save_number = fail_on_save_number

    def save_profile(self, profile: GeminiKeyProfile) -> None:
        self._save_count += 1
        if self._save_count == self._fail_on_save_number:
            raise RuntimeError("simulated metadata failure")
        super().save_profile(profile)


def test_import_keys_rolls_back_partial_batch_on_storage_failure() -> None:
    profiles = FailingProfiles(fail_on_save_number=2)
    secrets = MemorySecrets()
    registry = GeminiCredentialRegistry(profiles, secrets)

    try:
        registry.import_keys(
            (
                "fake-key-one-xxxxxxxxxxxxxxxxxxxxxxxx",
                "fake-key-two-xxxxxxxxxxxxxxxxxxxxxxxx",
            )
        )
    except CredentialStorageError as exc:
        assert str(exc) == "API key tidak dapat disimpan."
    else:
        raise AssertionError("expected credential storage failure")

    assert profiles.list_profiles() == ()
    assert secrets.items == {}


def test_import_keys_rejects_duplicate_lines_before_writing() -> None:
    profiles = MemoryProfiles()
    secrets = MemorySecrets()
    registry = GeminiCredentialRegistry(profiles, secrets)
    key = "fake-key-duplicate-xxxxxxxxxxxxxxxxxxxx"

    try:
        registry.import_keys((key, key))
    except ValueError as exc:
        assert "sama lebih dari sekali" in str(exc)
    else:
        raise AssertionError("expected duplicate-key validation failure")

    assert profiles.list_profiles() == ()
    assert secrets.items == {}


def test_active_profile_skips_orphaned_metadata_without_secret() -> None:
    profiles = MemoryProfiles()
    secrets = MemorySecrets()
    registry = GeminiCredentialRegistry(profiles, secrets)

    orphan = GeminiKeyProfile(
        profile_id="orphan",
        label="Lama",
        enabled=True,
        priority=1,
    )
    valid = GeminiKeyProfile(
        profile_id="valid",
        label="Aktif",
        enabled=True,
        priority=2,
    )
    profiles.save_profile(orphan)
    profiles.save_profile(valid)
    secrets.set_secret("valid", "fake-key-valid-xxxxxxxxxxxxxxxxxxxxxxxx")

    assert registry.active_profile() == valid
    assert registry.active_secret() == "fake-key-valid-xxxxxxxxxxxxxxxxxxxxxxxx"
