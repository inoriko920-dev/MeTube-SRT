from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QLockFile


class RuntimeDataLock:
    """Exclusive runtime ownership for one desktop data directory."""

    def __init__(self, data_directory: Path, *, stale_lock_ms: int = 30_000) -> None:
        directory = data_directory.expanduser().resolve(strict=False)
        directory.mkdir(parents=True, exist_ok=True)
        self._path = directory / ".metube-srt-runtime.lock"
        self._lock = QLockFile(str(self._path))
        self._lock.setStaleLockTime(stale_lock_ms)
        self._acquired = False

    @property
    def path(self) -> Path:
        return self._path

    @property
    def acquired(self) -> bool:
        return self._acquired

    def try_acquire(self) -> bool:
        if self._acquired:
            return True
        self._acquired = self._lock.tryLock(0)
        return self._acquired

    def release(self) -> None:
        if not self._acquired:
            return
        self._lock.unlock()
        self._acquired = False

    def __enter__(self) -> RuntimeDataLock:
        if not self.try_acquire():
            raise RuntimeError(f"data directory is already owned: {self._path.parent}")
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()
