from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from metube_srt_desktop.presentation.shell.main_window import MainWindow


def run_desktop(argv: Sequence[str] | None = None) -> int:
    existing = QApplication.instance()
    owns_application = existing is None
    app = (
        QApplication(list(argv) if argv is not None else sys.argv) if existing is None else existing
    )
    if not isinstance(app, QApplication):
        raise RuntimeError("existing Qt application is not QApplication")

    app.setApplicationName("MeTube-SRT Desktop")
    app.setOrganizationName("MeTube-SRT")
    window = MainWindow()
    window.show()

    if owns_application:
        return app.exec()
    return 0
