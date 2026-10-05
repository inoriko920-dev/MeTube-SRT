from __future__ import annotations

from pytestqt.qtbot import QtBot

from metube_srt_desktop.presentation.shell.main_window import MainWindow


def test_step09_reference_viewport_geometry(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(1440, 900)
    window.show()

    assert window.size().width() == 1440
    assert window.size().height() == 900
    assert window.navigation.width() == 188
    assert window.ai_workspace.width() == 318
