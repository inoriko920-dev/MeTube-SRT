from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QSplitter, QStackedWidget, QWidget

from metube_srt_desktop.application.ai_conversation import HumanlikeAIConversation
from metube_srt_desktop.application.gemini_credentials import GeminiCredentialRegistry
from metube_srt_desktop.application.ports.ai_provider import AIProviderPort
from metube_srt_desktop.application.ports.download_queue import QueueRuntimePort
from metube_srt_desktop.application.ports.source_resolver import SourceResolverPort
from metube_srt_desktop.presentation.components.ai_panel import AIWorkspace
from metube_srt_desktop.presentation.components.navigation_rail import NavigationRail
from metube_srt_desktop.presentation.controllers.ai_agent import AIAgentController
from metube_srt_desktop.presentation.controllers.download_queue import DownloadQueueController
from metube_srt_desktop.presentation.controllers.gemini_credentials import (
    GeminiCredentialsController,
)
from metube_srt_desktop.presentation.pages.api_keys.page import ApiKeysPage
from metube_srt_desktop.presentation.pages.download.page import DownloadPage
from metube_srt_desktop.presentation.pages.queue.page import QueuePage
from metube_srt_desktop.presentation.pages.settings.page import SettingsPage
from metube_srt_desktop.presentation.theme.stylesheet import build_stylesheet
from metube_srt_desktop.presentation.theme.tokens import TOKENS


class PageId(StrEnum):
    DOWNLOAD = "download"
    QUEUE = "queue"
    API_KEYS = "api_keys"  # pragma: allowlist secret
    SETTINGS = "settings"


class MainWindow(QMainWindow):
    def __init__(
        self,
        *,
        resolver: SourceResolverPort | None = None,
        queue: QueueRuntimePort | None = None,
        ai_conversation: HumanlikeAIConversation | None = None,
        credential_registry: GeminiCredentialRegistry | None = None,
        ai_provider: AIProviderPort | None = None,
    ) -> None:
        super().__init__()
        if (resolver is None) != (queue is None):
            raise ValueError("resolver and queue must be provided together")

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
        self.download_page = DownloadPage()
        self.queue_page = QueuePage()
        self.api_keys_page = ApiKeysPage()
        self._pages: dict[PageId, QWidget] = {
            PageId.DOWNLOAD: self.download_page,
            PageId.QUEUE: self.queue_page,
            PageId.API_KEYS: self.api_keys_page,
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

        self.download_controller: DownloadQueueController | None = None
        self.ai_controller: AIAgentController | None = None
        self.credentials_controller: GeminiCredentialsController | None = None

        if resolver is not None and queue is not None:
            self.download_controller = DownloadQueueController(
                self.download_page,
                self.queue_page,
                resolver,
                queue,
                parent=self,
            )

        if ai_conversation is not None and queue is not None:
            self.ai_controller = AIAgentController(
                self.ai_workspace,
                self.download_page,
                queue,
                ai_conversation,
                parent=self,
            )

        if credential_registry is not None and ai_provider is not None:
            self.credentials_controller = GeminiCredentialsController(
                self.api_keys_page,
                credential_registry,
                ai_provider,
                parent=self,
            )

        self.navigate(PageId.DOWNLOAD.value)

    @property
    def current_page_id(self) -> PageId:
        current = self.stack.currentWidget()
        for page_id, page in self._pages.items():
            if page is current:
                return page_id
        raise RuntimeError("current stacked page is not registered")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.download_controller is not None:
            self.download_controller.shutdown()
        super().closeEvent(event)

    def navigate(self, raw_page_id: str) -> None:
        page_id = PageId(raw_page_id)
        self.stack.setCurrentWidget(self._pages[page_id])
        self.navigation.set_active(page_id.value)
        self.ai_workspace.setVisible(page_id is PageId.DOWNLOAD)
        if page_id is PageId.DOWNLOAD and not self.ai_workspace.is_collapsed:
            self.ai_workspace.setFixedWidth(TOKENS.ai_panel_width)
