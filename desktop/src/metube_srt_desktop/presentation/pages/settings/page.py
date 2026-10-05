from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from metube_srt_desktop.presentation.components.page_header import PageHeader
from metube_srt_desktop.presentation.theme.tokens import TOKENS


class SettingsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page.settings")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(TOKENS.space_lg, TOKENS.space_lg, TOKENS.space_lg, TOKENS.space_lg)
        layout.setSpacing(TOKENS.space_md)
        layout.addWidget(PageHeader("Pengaturan", "Preferensi umum, download, AI, dan privasi."))

        general = QFrame()
        general.setProperty("card", True)
        form = QFormLayout(general)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(12)
        language = QComboBox()
        language.addItems(["Bahasa Indonesia"])
        concurrency = QSpinBox()
        concurrency.setRange(1, 4)
        concurrency.setValue(2)
        srt_default = QCheckBox("Aktifkan SRT untuk video baru")
        srt_default.setChecked(True)
        ai_approval = QCheckBox("Minta persetujuan sebelum AI menambahkan pekerjaan")
        ai_approval.setChecked(True)
        diagnostics = QCheckBox("Redaksi otomatis secret pada diagnostic")
        diagnostics.setChecked(True)
        form.addRow("Bahasa", language)
        form.addRow("Download bersamaan", concurrency)
        form.addRow("Subtitle", srt_default)
        form.addRow("AI Agent", ai_approval)
        form.addRow("Privasi", diagnostics)
        layout.addWidget(general)

        hint = QLabel("Perubahan pada layar ini masih fixture STEP 09 dan belum disimpan ke disk.")
        hint.setProperty("muted", True)
        layout.addWidget(hint)
        layout.addStretch(1)
