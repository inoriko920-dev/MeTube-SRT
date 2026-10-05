from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from metube_srt_desktop.presentation.components.page_header import PageHeader
from metube_srt_desktop.presentation.theme.tokens import TOKENS


class DownloadPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("page.download")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            TOKENS.space_lg, TOKENS.space_lg, TOKENS.space_lg, TOKENS.space_lg
        )
        layout.setSpacing(TOKENS.space_md)

        layout.addWidget(
            PageHeader(
                "Unduh",
                "Video tunggal, playlist, atau channel. Subtitle SRT opsional tanpa terjemahan otomatis.",
            )
        )

        card = QFrame()
        card.setProperty("card", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setObjectName("download.url_input")
        self.url_input.setPlaceholderText("Tempel URL YouTube…")
        resolve_button = QPushButton("Periksa")
        resolve_button.setObjectName("download.resolve_button")
        resolve_button.setProperty("role", "secondary")
        url_row.addWidget(self.url_input, 1)
        url_row.addWidget(resolve_button)
        card_layout.addLayout(url_row)

        options = QHBoxLayout()
        quality_label = QLabel("Kualitas")
        quality_label.setProperty("muted", True)
        self.quality_combo = QComboBox()
        self.quality_combo.setObjectName("download.quality")
        self.quality_combo.addItems(["Terbaik", "1080p", "720p", "480p"])
        self.subtitle_checkbox = QCheckBox("Download subtitle (SRT)")
        self.subtitle_checkbox.setObjectName("download.subtitle_srt")
        self.subtitle_checkbox.setChecked(True)
        options.addWidget(quality_label)
        options.addWidget(self.quality_combo)
        options.addSpacing(12)
        options.addWidget(self.subtitle_checkbox)
        options.addStretch(1)
        card_layout.addLayout(options)

        output_row = QHBoxLayout()
        output_label = QLabel("Simpan ke")
        output_label.setProperty("muted", True)
        self.output_path = QLineEdit(r"Downloads\MeTube-SRT")
        self.output_path.setObjectName("download.output_path")
        browse = QPushButton("Pilih folder")
        browse.setProperty("role", "secondary")
        output_row.addWidget(output_label)
        output_row.addWidget(self.output_path, 1)
        output_row.addWidget(browse)
        card_layout.addLayout(output_row)

        action_row = QHBoxLayout()
        note = QLabel("Manual > auto-generated asli > tanpa SRT")
        note.setProperty("muted", True)
        start = QPushButton("Tambahkan ke antrian")
        start.setObjectName("download.enqueue_button")
        start.setProperty("role", "primary")
        action_row.addWidget(note)
        action_row.addStretch(1)
        action_row.addWidget(start)
        card_layout.addLayout(action_row)
        layout.addWidget(card)

        state = QFrame()
        state.setProperty("card", True)
        state_layout = QVBoxLayout(state)
        state_layout.setContentsMargins(18, 20, 18, 20)
        state_layout.setSpacing(7)
        empty_title = QLabel("Siap menerima URL")
        empty_title.setProperty("sectionTitle", True)
        empty_text = QLabel(
            "Tempel satu URL, playlist, atau channel. Setelah diperiksa, item akan muncul di sini sebelum masuk antrian."
        )
        empty_text.setProperty("muted", True)
        empty_text.setWordWrap(True)
        state_layout.addWidget(empty_title)
        state_layout.addWidget(empty_text)
        state_layout.addStretch(1)
        layout.addWidget(state, 1)
