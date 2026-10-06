from pathlib import Path

from metube_srt_desktop.infrastructure.runtime_lock import RuntimeDataLock


def test_same_data_directory_allows_only_one_runtime(tmp_path: Path) -> None:
    first = RuntimeDataLock(tmp_path)
    second = RuntimeDataLock(tmp_path)

    assert first.try_acquire() is True
    assert second.try_acquire() is False

    first.release()
    assert second.try_acquire() is True
    second.release()


def test_different_data_directories_can_run_independently(tmp_path: Path) -> None:
    first = RuntimeDataLock(tmp_path / "one")
    second = RuntimeDataLock(tmp_path / "two")

    assert first.try_acquire() is True
    assert second.try_acquire() is True

    first.release()
    second.release()


def test_release_is_idempotent(tmp_path: Path) -> None:
    runtime_lock = RuntimeDataLock(tmp_path)
    assert runtime_lock.try_acquire() is True

    runtime_lock.release()
    runtime_lock.release()

    assert runtime_lock.acquired is False
