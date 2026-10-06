from __future__ import annotations

from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from math import ceil
from uuid import uuid4

from metube_srt_desktop.application.dto.gemini_credentials import GeminiKeyProfile
from metube_srt_desktop.application.ports.credentials import (
    CredentialCooldownError,
    CredentialSecretPort,
    CredentialStorageError,
    GeminiProfileRepositoryPort,
)
from metube_srt_desktop.application.redaction import redact_sensitive_text

_MAX_PROFILES = 100
_INVALID_PROFILE_STATUSES = {"tidak valid", "invalid"}


class GeminiCredentialRegistry:
    """Coordinate Gemini key metadata with OS-backed secret storage."""

    def __init__(
        self,
        profiles: GeminiProfileRepositoryPort,
        secrets: CredentialSecretPort,
    ) -> None:
        self._profiles = profiles
        self._secrets = secrets

    def list_profiles(self) -> tuple[GeminiKeyProfile, ...]:
        profiles = self._profiles.list_profiles()
        enriched: list[GeminiKeyProfile] = []
        for profile in profiles:
            try:
                secret = self._secrets.get_secret(profile.profile_id)
            except CredentialStorageError:
                available: bool | None = None
            else:
                available = secret is not None and bool(secret.strip())
            enriched.append(replace(profile, secret_available=available))
        return tuple(enriched)

    def add_profile(self, label: str, raw_key: str) -> GeminiKeyProfile:
        clean_label = label.strip()
        clean_key = raw_key.strip()
        if not clean_label:
            raise ValueError("Nama API key tidak boleh kosong.")
        if len(clean_key) < 20:
            raise ValueError("API key Gemini terlihat tidak valid.")
        if clean_label == clean_key or redact_sensitive_text(clean_label).secret_detected:
            raise ValueError("Nama profil tidak boleh berisi API key, token, atau cookie.")

        existing = self._profiles.list_profiles()
        if len(existing) >= _MAX_PROFILES:
            raise ValueError("Maksimal 100 API key Gemini.")
        if self._secret_already_exists(existing, clean_key):
            raise ValueError("API key Gemini ini sudah tersimpan.")

        profile = GeminiKeyProfile(
            profile_id=uuid4().hex,
            label=clean_label,
            enabled=True,
            priority=(max((item.priority for item in existing), default=0) + 1),
        )
        try:
            self._secrets.set_secret(profile.profile_id, clean_key)
            self._profiles.save_profile(profile)
        except Exception as exc:
            with suppress(Exception):
                self._secrets.delete_secret(profile.profile_id)
            if isinstance(exc, (CredentialStorageError, ValueError)):
                raise
            raise CredentialStorageError("API key tidak dapat disimpan.") from exc
        return profile

    def import_keys(self, raw_keys: tuple[str, ...]) -> tuple[GeminiKeyProfile, ...]:
        clean_keys = tuple(key.strip() for key in raw_keys if key.strip())
        if not clean_keys:
            raise ValueError("File TXT tidak berisi API key.")
        if any(len(key) < 20 for key in clean_keys):
            raise ValueError("Salah satu API key Gemini terlihat tidak valid.")
        if len(set(clean_keys)) != len(clean_keys):
            raise ValueError("File TXT berisi API key yang sama lebih dari sekali.")

        existing_count = len(self._profiles.list_profiles())
        if existing_count + len(clean_keys) > _MAX_PROFILES:
            raise ValueError("Jumlah API key akan melebihi batas 100.")

        created: list[GeminiKeyProfile] = []
        try:
            for index, key in enumerate(clean_keys, start=1):
                profile = self.add_profile(f"Gemini {existing_count + index:02d}", key)
                created.append(profile)
        except Exception:
            self._rollback_profiles(created)
            raise
        return tuple(created)

    def active_profile(self) -> GeminiKeyProfile | None:
        active = self._active_profile_and_secret()
        return None if active is None else active[0]

    def active_secret(self) -> str | None:
        credential = self.active_credential()
        return None if credential is None else credential[1]

    def active_credential(self) -> tuple[str, str] | None:
        active = self._active_profile_and_secret()
        if active is None:
            return None
        profile, secret = active
        retry_after = _cooldown_retry_after_seconds(profile.cooldown_until)
        if retry_after is not None:
            raise CredentialCooldownError(retry_after)
        return profile.profile_id, secret

    def secret_for_profile(self, profile_id: str) -> str | None:
        if not profile_id.strip():
            raise ValueError("profile_id must be non-empty")
        if not any(profile.profile_id == profile_id for profile in self._profiles.list_profiles()):
            return None
        secret = self._secrets.get_secret(profile_id)
        if secret is None or not secret.strip():
            return None
        return secret.strip()

    def mark_status(
        self,
        profile_id: str,
        status: str,
        *,
        clear_cooldown: bool = False,
    ) -> None:
        profile = self._profile_by_id(profile_id)
        if profile is None:
            return

        active_cooldown = _cooldown_retry_after_seconds(profile.cooldown_until)
        requested_active = status.strip().casefold() == "aktif"
        if requested_active and active_cooldown is not None and not clear_cooldown:
            # A late targeted success must not erase a newer 429 cooldown.
            status = profile.status

        updated = replace(
            profile,
            status=status,
            last_tested_at=datetime.now(UTC).isoformat(timespec="seconds"),
            cooldown_until=None if clear_cooldown else profile.cooldown_until,
            secret_available=None,
        )
        self._profiles.save_profile(updated)

    def mark_cooldown(self, profile_id: str, *, seconds: int = 60) -> None:
        if seconds < 1:
            raise ValueError("cooldown seconds must be >= 1")
        profile = self._profile_by_id(profile_id)
        if profile is None:
            return
        now = datetime.now(UTC)
        updated = replace(
            profile,
            status="Rate Limit",
            last_tested_at=now.isoformat(timespec="seconds"),
            cooldown_until=(now + timedelta(seconds=seconds)).isoformat(timespec="seconds"),
            secret_available=None,
        )
        self._profiles.save_profile(updated)

    def mark_active_status(self, status: str) -> None:
        profile = self.active_profile()
        if profile is None:
            return
        self.mark_status(
            profile.profile_id,
            status,
            clear_cooldown=status.strip().casefold() == "aktif",
        )

    def mark_active_cooldown(self, *, seconds: int = 60) -> None:
        profile = self.active_profile()
        if profile is None:
            return
        self.mark_cooldown(profile.profile_id, seconds=seconds)

    def _profile_by_id(self, profile_id: str) -> GeminiKeyProfile | None:
        for profile in self._profiles.list_profiles():
            if profile.profile_id == profile_id:
                return profile
        return None

    def _secret_already_exists(
        self,
        profiles: tuple[GeminiKeyProfile, ...],
        candidate: str,
    ) -> bool:
        for profile in profiles:
            stored = self._secrets.get_secret(profile.profile_id)
            if stored is not None and compare_digest(stored.strip(), candidate):
                return True
        return False

    def _active_profile_and_secret(self) -> tuple[GeminiKeyProfile, str] | None:
        for profile in self._profiles.list_profiles():
            if not profile.enabled:
                continue
            if profile.status.strip().casefold() in _INVALID_PROFILE_STATUSES:
                continue
            secret = self._secrets.get_secret(profile.profile_id)
            if secret is not None and secret.strip():
                return profile, secret.strip()
        return None

    def _rollback_profiles(self, profiles: list[GeminiKeyProfile]) -> None:
        rollback_failed = False
        for profile in reversed(profiles):
            try:
                self._profiles.delete_profile(profile.profile_id)
            except Exception:
                rollback_failed = True
            try:
                self._secrets.delete_secret(profile.profile_id)
            except Exception:
                rollback_failed = True
        if rollback_failed:
            raise CredentialStorageError(
                "Import API key gagal dan rollback tidak selesai sepenuhnya."
            )


def _cooldown_retry_after_seconds(cooldown_until: str | None) -> int | None:
    if cooldown_until is None or not cooldown_until.strip():
        return None
    try:
        until = datetime.fromisoformat(cooldown_until)
    except ValueError:
        return None
    if until.tzinfo is None:
        until = until.replace(tzinfo=UTC)
    remaining = (until.astimezone(UTC) - datetime.now(UTC)).total_seconds()
    if remaining <= 0:
        return None
    return max(1, ceil(remaining))
