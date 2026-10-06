import subprocess
import sys
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


_LOCK_HOLDER_SCRIPT = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "from metube_srt_desktop.infrastructure.runtime_lock import RuntimeDataLock\n"
    "lock = RuntimeDataLock(Path(sys.argv[1]), stale_lock_ms=100)\n"
    "ok = lock.try_acquire()\n"
    "print('LOCKED' if ok else 'BUSY', flush=True)\n"
    "if not ok: raise SystemExit(3)\n"
    "time.sleep(60)\n"
)

_LOCK_PROBE_SCRIPT = (
    "import sys\n"
    "from pathlib import Path\n"
    "from metube_srt_desktop.infrastructure.runtime_lock import RuntimeDataLock\n"
    "lock = RuntimeDataLock(Path(sys.argv[1]), stale_lock_ms=100)\n"
    "ok = lock.try_acquire()\n"
    "print('ACQUIRED' if ok else 'BUSY', flush=True)\n"
    "if ok: lock.release()\n"
    "raise SystemExit(0 if ok else 2)\n"
)

_LOCK_RECOVERY_SCRIPT = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "from metube_srt_desktop.infrastructure.runtime_lock import RuntimeDataLock\n"
    "deadline = time.monotonic() + 5.0\n"
    "while time.monotonic() < deadline:\n"
    "    lock = RuntimeDataLock(Path(sys.argv[1]), stale_lock_ms=100)\n"
    "    if lock.try_acquire():\n"
    "        print('RECOVERED', flush=True)\n"
    "        lock.release()\n"
    "        raise SystemExit(0)\n"
    "    time.sleep(0.05)\n"
    "print('STALE', flush=True)\n"
    "raise SystemExit(4)\n"
)


def _start_lock_holder(data_directory: Path) -> subprocess.Popen[str]:
    process = subprocess.Popen(
        [sys.executable, "-c", _LOCK_HOLDER_SCRIPT, str(data_directory)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    assert process.stdout.readline().strip() == "LOCKED"
    return process


def _kill_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is None:
        process.kill()
    process.communicate(timeout=5)


def test_runtime_lock_is_exclusive_across_processes(tmp_path: Path) -> None:
    holder = _start_lock_holder(tmp_path)
    try:
        probe = subprocess.run(
            [sys.executable, "-c", _LOCK_PROBE_SCRIPT, str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        assert probe.returncode == 2
        assert probe.stdout.strip() == "BUSY"
    finally:
        _kill_process(holder)


def test_runtime_lock_recovers_after_owner_process_crash(tmp_path: Path) -> None:
    holder = _start_lock_holder(tmp_path)
    _kill_process(holder)

    recovery = subprocess.run(
        [sys.executable, "-c", _LOCK_RECOVERY_SCRIPT, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )

    assert recovery.returncode == 0, recovery.stderr
    assert recovery.stdout.strip() == "RECOVERED"
