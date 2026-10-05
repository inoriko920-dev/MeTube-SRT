from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QTableView, QVBoxLayout, QWidget

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
                "Kelola sampai 100 profil API key. Nilai secret tidak pernah ditampilkan penuh.",
            )
        )

        actions = QHBoxLayout()
        for text, object_name, role in (
            ("Tambah key", "api_keys.add", "primary"),
            ("Import", "api_keys.import", "secondary"),
            ("Tes key aktif", "api_keys.test", "secondary"),
        ):
            button = QPushButton(text)
            button.setObjectName(object_name)
            button.setProperty("role", role)
            actions.addWidget(button)
        actions.addStretch(1)
        layout.addLayout(actions)

        self.table = QTableView()
        self.table.setObjectName("api_keys.table")
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        model = QStandardItemModel(0, 5, self)
        model.setHorizontalHeaderLabels(
            ["Nama", "API key", "Status", "Prioritas", "Terakhir diuji"]
        )
        fixtures = [
            ("Gemini Utama", "AIza••••••••7Q", "Aktif", "1", "Baru saja"),
            ("Cadangan 02", "AIza••••••••K2", "Rate Limit", "2", "2 menit lalu"),
            ("Cadangan 03", "AIza••••••••P9", "Belum diuji", "3", "—"),
        ]
        for row in fixtures:
            model.appendRow([QStandardItem(value) for value in row])
        self.table.setModel(model)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
