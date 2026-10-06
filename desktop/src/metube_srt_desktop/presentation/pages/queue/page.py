from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from metube_srt_desktop.presentation.components.page_header import PageHeader
from metube_srt_desktop.presentation.theme.tokens import TOKENS


class QueuePage(QWidget):
    cancel_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page.queue")
        self._row_by_job_id: dict[str, int] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            TOKENS.space_lg, TOKENS.space_lg, TOKENS.space_lg, TOKENS.space_lg
        )
        layout.setSpacing(TOKENS.space_md)
        layout.addWidget(PageHeader("Antrian", "Pantau pekerjaan aktif, selesai, dan gagal."))

        stats = QHBoxLayout()
        self.active_count = self._add_stat_card(stats, "Aktif", "success")
        self.waiting_count = self._add_stat_card(stats, "Menunggu", "warning")
        self.failed_count = self._add_stat_card(stats, "Gagal", "danger")
        stats.addStretch(1)
        layout.addLayout(stats)

        self.table = QTableView()
        self.table.setObjectName("queue.table")
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.model = QStandardItemModel(0, 5, self)
        self.model.setHorizontalHeaderLabels(["Judul", "Jenis", "Status", "Progress", "SRT"])
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.cancel_action = QAction("Batalkan pekerjaan terpilih", self.table)
        self.cancel_action.setShortcut(QKeySequence("Delete"))
        self.cancel_action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.cancel_action.triggered.connect(self.request_cancel_selected)
        self.table.addAction(self.cancel_action)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

        layout.addWidget(self.table, 1)

    def set_counts(self, *, active: int, waiting: int, failed: int) -> None:
        self.active_count.setText(str(active))
        self.waiting_count.setText(str(waiting))
        self.failed_count.setText(str(failed))

    def upsert_job(
        self,
        *,
        job_id: str,
        title: str,
        kind: str,
        status: str,
        progress: str,
        srt: str,
    ) -> None:
        row = self._row_by_job_id.get(job_id)
        values = (title, kind, status, progress, srt)

        if row is None:
            row = self.model.rowCount()
            items = [QStandardItem(value) for value in values]
            items[0].setData(job_id, Qt.ItemDataRole.UserRole)
            self.model.appendRow(items)
            self._row_by_job_id[job_id] = row
            return

        for column, value in enumerate(values):
            item = self.model.item(row, column)
            if item.text() != value:
                item.setText(value)

    def request_cancel_selected(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return

        first = self.model.item(rows[0].row(), 0)
        job_id = first.data(Qt.ItemDataRole.UserRole)
        if isinstance(job_id, str) and job_id:
            self.cancel_requested.emit(job_id)

    def _add_stat_card(
        self,
        layout: QHBoxLayout,
        title: str,
        badge: str,
    ) -> QLabel:
        card = QFrame()
        card.setProperty("card", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        label = QLabel(title)
        label.setProperty("muted", True)
        number = QLabel("0")
        number.setProperty("badge", badge)
        card_layout.addWidget(label)
        card_layout.addWidget(number)
        layout.addWidget(card)
        return number
