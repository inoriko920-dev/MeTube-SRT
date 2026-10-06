from pathlib import Path

from pytestqt.qtbot import QtBot

from metube_srt_desktop.bootstrap.app_bootstrap import build_runtime_window


def test_bootstrap_composes_real_download_runtime_without_starting_network(
    qtbot: QtBot,
    tmp_path: Path,
) -> None:
    window, queue = build_runtime_window(data_directory=tmp_path)
    qtbot.addWidget(window)

    try:
        assert window.download_controller is not None
        assert queue.snapshots() == ()
        assert (tmp_path / "app.db").exists()
    finally:
        queue.shutdown(wait=True)
