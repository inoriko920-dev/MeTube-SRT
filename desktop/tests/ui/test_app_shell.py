from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QWidget
from pytestqt.qtbot import QtBot

from metube_srt_desktop.presentation.shell.main_window import MainWindow, PageId


def test_shell_has_frozen_global_navigation(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    labels = [
        window.navigation.button("download").text(),
        window.navigation.button("queue").text(),
        window.navigation.button("api_keys").text(),
        window.navigation.button("settings").text(),
    ]

    assert labels == ["Unduh", "Antrian", "API Gemini", "Pengaturan"]
    assert window.current_page_id is PageId.DOWNLOAD
    assert window.ai_workspace.isVisible()


def test_navigation_uses_stacked_pages_and_ai_only_on_download(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    queue_button = window.findChild(QPushButton, "nav.queue")
    assert queue_button is not None
    queue_button.click()
    assert window.current_page_id is PageId.QUEUE
    assert not window.ai_workspace.isVisible()

    download_button = window.findChild(QPushButton, "nav.download")
    assert download_button is not None
    download_button.click()
    assert window.current_page_id is PageId.DOWNLOAD
    assert window.ai_workspace.isVisible()


def test_ai_workspace_collapses_without_changing_page(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    collapse = window.findChild(QPushButton, "ai.collapse_button")
    assert collapse is not None
    collapse.click()

    assert window.ai_workspace.is_collapsed
    assert window.current_page_id is PageId.DOWNLOAD


def test_frozen_core_object_names_exist(qtbot: QtBot) -> None:
    window = MainWindow()
    qtbot.addWidget(window)

    expected = (
        "download.url_input",
        "download.subtitle_srt",
        "download.enqueue_button",
        "queue.table",
        "api_keys.table",
        "ai_prompt",
    )
    for object_name in expected:
        assert window.findChild(QWidget, object_name) is not None
