from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QFrame, QHBoxLayout, QLabel, QTableView, QVBoxLayout, QWidget

from metube_srt_desktop.presentation.components.page_header import PageHeader
from metube_srt_desktop.presentation.theme.tokens import TOKENS


class QueuePage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page.queue")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(TOKENS.space_lg, TOKENS.space_lg, TOKENS.space_lg, TOKENS.space_lg)
        layout.setSpacing(TOKENS.space_md)
        layout.addWidget(PageHeader("Antrian", "Pantau pekerjaan aktif, selesai, dan gagal."))

        stats = QHBoxLayout()
        for title, value, badge in (
            ("Aktif", "2", "success"),
            ("Menunggu", "3", "warning"),
            ("Gagal", "1", "danger"),
        ):
            card = QFrame()
            card.setProperty("card", True)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            label = QLabel(title)
            label.setProperty("muted", True)
            number = QLabel(value)
            number.setProperty("badge", badge)
            card_layout.addWidget(label)
            card_layout.addWidget(number)
            stats.addWidget(card)
        stats.addStretch(1)
        layout.addLayout(stats)

        self.table = QTableView()
        self.table.setObjectName("queue.table")
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        model = QStandardItemModel(0, 5, self)
        model.setHorizontalHeaderLabels(["Judul", "Jenis", "Status", "Progress", "SRT"])
        fixtures = [
            ("Dokumenter — Episode 1", "Video", "Mengunduh", "64%", "Manual"),
            ("Playlist Belajar", "Playlist", "Menunggu", "0%", "Auto asli"),
            ("Channel Arsip", "Channel", "Gagal", "18%", "Tidak ada"),
        ]
        for row in fixtures:
            model.appendRow([QStandardItem(value) for value in row])
        self.table.setModel(model)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
