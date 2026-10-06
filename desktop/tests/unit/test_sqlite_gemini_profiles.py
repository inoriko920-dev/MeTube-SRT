from __future__ import annotations

from pathlib import Path

from metube_srt_desktop.adapters.storage.sqlite_gemini_profiles import (
    SQLiteGeminiProfileRepository,
)
from metube_srt_desktop.adapters.storage.sqlite_queue import SQLiteQueueStorage
from metube_srt_desktop.application.dto.gemini_credentials import GeminiKeyProfile


def test_gemini_profile_metadata_coexists_with_queue_database(tmp_path: Path) -> None:
    database = tmp_path / "app.db"
    queue_storage = SQLiteQueueStorage(database)
    profiles = SQLiteGeminiProfileRepository(database)

    profiles.save_profile(
        GeminiKeyProfile(
            profile_id="profile-1",
            label="Gemini Utama",
            enabled=True,
            priority=1,
            status="Aktif",
        )
    )

    loaded = profiles.list_profiles()
    assert loaded == (
        GeminiKeyProfile(
            profile_id="profile-1",
            label="Gemini Utama",
            enabled=True,
            priority=1,
            status="Aktif",
        ),
    )
    assert queue_storage.load_entries() == ()
