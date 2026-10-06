from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTableView, QVBoxLayout, QWidget

from metube_srt_desktop.application.dto.gemini_credentials import GeminiKeyProfile
from metube_srt_desktop.presentation.components.page_header import PageHeader
from metube_srt_desktop.presentation.theme.tokens import TOKENS


class ApiKeysPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page.api_keys")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            TOKENS.space_lg, TOKENS.space_lg, TOKENS.space_lg, TOKENS.space_lg
        )
        layout.setSpacing(TOKENS.space_md)
        layout.addWidget(
            PageHeader(
                "API Gemini",
                "Kelola sampai 100 profil API key. Secret disimpan di penyimpanan aman Windows.",
            )
        )

        actions = QHBoxLayout()
        self.add_button = QPushButton("Tambah key")
        self.add_button.setObjectName("api_keys.add")
        self.add_button.setProperty("role", "primary")
        self.import_button = QPushButton("Import TXT")
        self.import_button.setObjectName("api_keys.import")
        self.import_button.setProperty("role", "secondary")
        self.test_button = QPushButton("Tes key aktif")
        self.test_button.setObjectName("api_keys.test")
        self.test_button.setProperty("role", "secondary")
        for button in (self.add_button, self.import_button, self.test_button):
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.table = QTableView()
        self.table.setObjectName("api_keys.table")
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.model = QStandardItemModel(0, 5, self)
        self.model.setHorizontalHeaderLabels(
            ["Nama", "API key", "Status", "Prioritas", "Terakhir diuji"]
        )
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

    def set_profiles(self, profiles: tuple[GeminiKeyProfile, ...]) -> None:
        self.model.removeRows(0, self.model.rowCount())
        for profile in profiles:
            last_tested = profile.last_tested_at or "—"
            self.model.appendRow(
                [
                    QStandardItem(profile.label),
                    QStandardItem(_secret_status(profile)),
                    QStandardItem(profile.status),
                    QStandardItem(str(profile.priority)),
                    QStandardItem(last_tested),
                ]
            )



def _secret_status(profile: GeminiKeyProfile) -> str:
    if profile.secret_available is True:
        return "Tersimpan aman"
    if profile.secret_available is False:
        return "Tidak tersedia di Windows ini"
    return "Belum diverifikasi"
