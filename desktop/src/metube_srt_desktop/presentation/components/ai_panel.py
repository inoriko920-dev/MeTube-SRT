from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from metube_srt_desktop.presentation.theme.tokens import TOKENS


class AIWorkspace(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ai_workspace")
        self.setMinimumWidth(TOKENS.ai_collapsed_width)
        self.setMaximumWidth(TOKENS.ai_panel_width)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._collapsed = False

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 16, 12, 16)
        root.setSpacing(12)

        head = QHBoxLayout()
        title = QLabel("AI Agent")
        title.setProperty("sectionTitle", True)
        status = QLabel("Siap")
        status.setObjectName("ai.status")
        status.setProperty("badge", "success")
        self._collapse_button = QPushButton("<")
        self._collapse_button.setObjectName("ai.collapse_button")
        self._collapse_button.setProperty("role", "ghost")
        self._collapse_button.setToolTip("Ciutkan panel AI")
        self._collapse_button.clicked.connect(self.toggle_collapsed)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(status)
        head.addWidget(self._collapse_button)
        root.addLayout(head)

        self._body = QWidget()
        body = QVBoxLayout(self._body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)

        intro = QLabel(
            "Berikan perintah download dengan bahasa biasa. AI hanya menyiapkan rencana; "
            "download tetap dijalankan oleh engine aplikasi."
        )
        intro.setProperty("muted", True)
        intro.setWordWrap(True)
        body.addWidget(intro)

        suggestion = QFrame()
        suggestion.setProperty("softCard", True)
        suggestion_layout = QVBoxLayout(suggestion)
        suggestion_layout.setContentsMargins(10, 10, 10, 10)
        suggestion_layout.addWidget(QLabel("Contoh"))
        example = QLabel("“Download playlist ini 1080p + SRT asli.”")
        example.setWordWrap(True)
        example.setProperty("muted", True)
        suggestion_layout.addWidget(example)
        body.addWidget(suggestion)

        self.prompt = QTextEdit()
        self.prompt.setObjectName("ai_prompt")
        self.prompt.setPlaceholderText("Tulis perintah download…")
        self.prompt.setFixedHeight(108)
        body.addWidget(self.prompt)

        send = QPushButton("Buat rencana")
        send.setObjectName("ai.plan_button")
        send.setProperty("role", "primary")
        body.addWidget(send)
        body.addStretch(1)
        root.addWidget(self._body, 1)

        self._collapsed_label = QLabel("AI")
        self._collapsed_label.setObjectName("ai.collapsed_label")
        self._collapsed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._collapsed_label.hide()
        root.addWidget(self._collapsed_label, 1)

    @property
    def is_collapsed(self) -> bool:
        return self._collapsed

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self._body.setVisible(not collapsed)
        self._collapsed_label.setVisible(collapsed)
        self._collapse_button.setText(">" if collapsed else "<")
        self._collapse_button.setToolTip("Buka panel AI" if collapsed else "Ciutkan panel AI")
        self.setFixedWidth(TOKENS.ai_collapsed_width if collapsed else TOKENS.ai_panel_width)
