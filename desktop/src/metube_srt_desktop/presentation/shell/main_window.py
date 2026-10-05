from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QSplitter, QStackedWidget, QWidget

from metube_srt_desktop.presentation.components.ai_panel import AIWorkspace
from metube_srt_desktop.presentation.components.navigation_rail import NavigationRail
from metube_srt_desktop.presentation.pages.api_keys.page import ApiKeysPage
from metube_srt_desktop.presentation.pages.download.page import DownloadPage
from metube_srt_desktop.presentation.pages.queue.page import QueuePage
from metube_srt_desktop.presentation.pages.settings.page import SettingsPage
from metube_srt_desktop.presentation.theme.stylesheet import build_stylesheet
from metube_srt_desktop.presentation.theme.tokens import TOKENS


class PageId(StrEnum):
    DOWNLOAD = "download"
    QUEUE = "queue"
    API_KEYS = "api_keys"
    SETTINGS = "settings"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("main_window")
        self.setWindowTitle("MeTube-SRT Desktop")
        self.resize(1440, 900)
        self.setMinimumSize(1180, 720)
        self.setStyleSheet(build_stylesheet())

        root = QWidget()
        root.setObjectName("app_root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        self.navigation = NavigationRail(self.navigate)
        root_layout.addWidget(self.navigation)

        self.stack = QStackedWidget()
        self.stack.setObjectName("page_stack")
        self._pages: dict[PageId, QWidget] = {
            PageId.DOWNLOAD: DownloadPage(),
            PageId.QUEUE: QueuePage(),
            PageId.API_KEYS: ApiKeysPage(),
            PageId.SETTINGS: SettingsPage(),
        }
        for page in self._pages.values():
            self.stack.addWidget(page)

        self.ai_workspace = AIWorkspace()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("content_splitter")
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self.stack)
        self.splitter.addWidget(self.ai_workspace)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([1100, TOKENS.ai_panel_width])
        root_layout.addWidget(self.splitter, 1)

        self.navigate(PageId.DOWNLOAD.value)

    @property
    def current_page_id(self) -> PageId:
        current = self.stack.currentWidget()
        for page_id, page in self._pages.items():
            if page is current:
                return page_id
        raise RuntimeError("current stacked page is not registered")

    def navigate(self, raw_page_id: str) -> None:
        page_id = PageId(raw_page_id)
        self.stack.setCurrentWidget(self._pages[page_id])
        self.navigation.set_active(page_id.value)
        self.ai_workspace.setVisible(page_id is PageId.DOWNLOAD)
        if page_id is PageId.DOWNLOAD and not self.ai_workspace.is_collapsed:
            self.ai_workspace.setFixedWidth(TOKENS.ai_panel_width)
