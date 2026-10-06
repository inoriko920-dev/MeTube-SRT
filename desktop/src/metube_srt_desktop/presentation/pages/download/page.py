from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
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
                "Video tunggal, playlist, atau channel. "
                "Subtitle SRT opsional tanpa terjemahan otomatis.",
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
        self.resolve_button = QPushButton("Periksa")
        self.resolve_button.setObjectName("download.resolve_button")
        self.resolve_button.setProperty("role", "secondary")
        url_row.addWidget(self.url_input, 1)
        url_row.addWidget(self.resolve_button)
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
        self.output_path = QLineEdit(_default_output_directory())
        self.output_path.setObjectName("download.output_path")
        self.browse_button = QPushButton("Pilih folder")
        self.browse_button.setProperty("role", "secondary")
        self.browse_button.clicked.connect(self._choose_output_directory)
        output_row.addWidget(output_label)
        output_row.addWidget(self.output_path, 1)
        output_row.addWidget(self.browse_button)
        card_layout.addLayout(output_row)

        action_row = QHBoxLayout()
        note = QLabel("Manual > auto-generated asli > tanpa SRT")
        note.setProperty("muted", True)
        self.enqueue_button = QPushButton("Tambahkan ke antrian")
        self.enqueue_button.setObjectName("download.enqueue_button")
        self.enqueue_button.setProperty("role", "primary")
        action_row.addWidget(note)
        action_row.addStretch(1)
        action_row.addWidget(self.enqueue_button)
        card_layout.addLayout(action_row)
        layout.addWidget(card)

        state = QFrame()
        state.setProperty("card", True)
        state_layout = QVBoxLayout(state)
        state_layout.setContentsMargins(18, 20, 18, 20)
        state_layout.setSpacing(7)
        self.state_title = QLabel("Siap menerima URL")
        self.state_title.setProperty("sectionTitle", True)
        self.state_text = QLabel(
            "Tempel satu URL, playlist, atau channel. Setelah diperiksa, "
            "item akan muncul di sini sebelum masuk antrian."
        )
        self.state_text.setProperty("muted", True)
        self.state_text.setWordWrap(True)
        state_layout.addWidget(self.state_title)
        state_layout.addWidget(self.state_text)
        state_layout.addStretch(1)
        layout.addWidget(state, 1)

    def set_busy(self, busy: bool) -> None:
        self.resolve_button.setDisabled(busy)
        self.enqueue_button.setDisabled(busy)
        self.url_input.setDisabled(busy)
        self.quality_combo.setDisabled(busy)
        self.subtitle_checkbox.setDisabled(busy)
        self.output_path.setDisabled(busy)
        self.browse_button.setDisabled(busy)

    def show_resolving(self) -> None:
        self.state_title.setText("Memeriksa URL…")
        self.state_text.setText(
            "Membaca metadata video, playlist, atau channel tanpa mengunduh media."
        )

    def show_resolved(self, title: str, *, item_count: int) -> None:
        self.state_title.setText("Siap ditambahkan ke antrian")
        self.state_text.setText(f"{title} • {item_count} video ditemukan.")

    def show_enqueuing(self) -> None:
        self.state_title.setText("Menambahkan ke antrian…")
        self.state_text.setText("Membekukan opsi kualitas dan subtitle untuk setiap video.")

    def show_queued(self, item_count: int) -> None:
        self.state_title.setText("Ditambahkan ke antrian")
        self.state_text.setText(f"{item_count} video sudah masuk ke antrian download.")

    def show_error(self, message: str) -> None:
        self.state_title.setText("Tidak dapat melanjutkan")
        self.state_text.setText(message)

    def _choose_output_directory(self) -> None:
        current = self.output_path.text().strip()
        selected = QFileDialog.getExistingDirectory(
            self,
            "Pilih folder download",
            current,
        )
        if selected:
            self.output_path.setText(selected)


def _default_output_directory() -> str:
    raw_downloads = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.DownloadLocation
    )
    base = Path(raw_downloads) if raw_downloads else Path.home() / "Downloads"
    return str((base / "MeTube-SRT").resolve(strict=False))
