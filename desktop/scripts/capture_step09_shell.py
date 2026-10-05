from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtWidgets import QApplication

from metube_srt_desktop.presentation.shell.main_window import MainWindow


def main() -> int:
    output_dir = Path(os.environ.get("STEP09_SCREENSHOT_DIR", "build/step09-evidence"))
    output_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    if not isinstance(app, QApplication):
        raise RuntimeError("existing Qt application is not QApplication")

    window = MainWindow()
    window.resize(1440, 900)
    window.show()
    app.processEvents()

    output = output_dir / "step09-app-shell.png"
    if not window.grab().save(str(output), "PNG"):
        raise RuntimeError(f"failed to save screenshot: {output}")
    print(output.resolve())
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
