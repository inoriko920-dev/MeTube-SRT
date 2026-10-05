from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QButtonGroup, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from metube_srt_desktop.presentation.theme.tokens import TOKENS


class NavigationRail(QFrame):
    def __init__(self, on_navigate: Callable[[str], None], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navigation_rail")
        self.setFixedWidth(TOKENS.navigation_width)
        self._buttons: dict[str, QPushButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(6)

        brand = QLabel("MeTube-SRT")
        brand.setObjectName("brand_title")
        subtitle = QLabel("Desktop")
        subtitle.setObjectName("brand_subtitle")
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        for page_id, label in (
            ("download", "Unduh"),
            ("queue", "Antrian"),
            ("api_keys", "API Gemini"),
            ("settings", "Pengaturan"),
        ):
            button = QPushButton(label)
            button.setObjectName(f"nav.{page_id}")
            button.setProperty("nav", True)
            button.setCheckable(True)
            button.setMinimumHeight(40)
            button.clicked.connect(lambda _checked=False, pid=page_id: on_navigate(pid))
            self._group.addButton(button)
            self._buttons[page_id] = button
            layout.addWidget(button)

        layout.addStretch(1)
        version = QLabel("Native desktop • STEP 09")
        version.setProperty("muted", True)
        version.setWordWrap(True)
        layout.addWidget(version)

        self.set_active("download")

    def set_active(self, page_id: str) -> None:
        button = self._buttons.get(page_id)
        if button is None:
            raise KeyError(f"unknown navigation page: {page_id}")
        button.setChecked(True)

    def button(self, page_id: str) -> QPushButton:
        return self._buttons[page_id]
