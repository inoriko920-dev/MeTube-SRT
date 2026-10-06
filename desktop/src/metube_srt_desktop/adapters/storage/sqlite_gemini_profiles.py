from __future__ import annotations

import sqlite3
from pathlib import Path

from metube_srt_desktop.application.dto.gemini_credentials import GeminiKeyProfile
from metube_srt_desktop.application.ports.credentials import (
    CredentialStorageError,
    GeminiProfileRepositoryPort,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS gemini_profiles (
    profile_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    priority INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL,
    last_tested_at TEXT,
    cooldown_until TEXT
);
"""


class SQLiteGeminiProfileRepository(GeminiProfileRepositoryPort):
    """Persist Gemini key metadata only; raw keys remain in OS keyring."""

    def __init__(self, database_path: str | Path) -> None:
        self._database_path = Path(database_path).expanduser()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def list_profiles(self) -> tuple[GeminiKeyProfile, ...]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT
                        profile_id,
                        label,
                        enabled,
                        priority,
                        status,
                        last_tested_at,
                        cooldown_until
                    FROM gemini_profiles
                    ORDER BY priority ASC
                    """
                ).fetchall()
        except sqlite3.Error as exc:
            raise CredentialStorageError("Metadata API Gemini tidak dapat dibaca.") from exc

        return tuple(
            GeminiKeyProfile(
                profile_id=str(row["profile_id"]),
                label=str(row["label"]),
                enabled=bool(row["enabled"]),
                priority=int(row["priority"]),
                status=str(row["status"]),
                last_tested_at=(
                    None if row["last_tested_at"] is None else str(row["last_tested_at"])
                ),
                cooldown_until=(
                    None if row["cooldown_until"] is None else str(row["cooldown_until"])
                ),
            )
            for row in rows
        )

    def save_profile(self, profile: GeminiKeyProfile) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO gemini_profiles (
                        profile_id, label, enabled, priority, status, last_tested_at, cooldown_until
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(profile_id) DO UPDATE SET
                        label=excluded.label,
                        enabled=excluded.enabled,
                        priority=excluded.priority,
                        status=excluded.status,
                        last_tested_at=excluded.last_tested_at,
                        cooldown_until=excluded.cooldown_until
                    """,
                    (
                        profile.profile_id,
                        profile.label,
                        int(profile.enabled),
                        profile.priority,
                        profile.status,
                        profile.last_tested_at,
                        profile.cooldown_until,
                    ),
                )
        except sqlite3.Error as exc:
            raise CredentialStorageError("Metadata API Gemini tidak dapat disimpan.") from exc

    def delete_profile(self, profile_id: str) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    "DELETE FROM gemini_profiles WHERE profile_id = ?",
                    (profile_id,),
                )
        except sqlite3.Error as exc:
            raise CredentialStorageError("Metadata API Gemini tidak dapat dihapus.") from exc

    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.executescript(_SCHEMA)
                columns = {
                    str(row["name"])
                    for row in connection.execute("PRAGMA table_info(gemini_profiles)").fetchall()
                }
                if "cooldown_until" not in columns:
                    connection.execute("ALTER TABLE gemini_profiles ADD COLUMN cooldown_until TEXT")
        except sqlite3.Error as exc:
            raise CredentialStorageError("Metadata API Gemini tidak dapat diinisialisasi.") from exc

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection
