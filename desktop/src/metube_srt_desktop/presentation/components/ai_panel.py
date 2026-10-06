from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
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
        self.status_label = QLabel("Siap")
        self.status_label.setObjectName("ai.status")
        self.status_label.setProperty("badge", "success")
        self._collapse_button = QPushButton("<")
        self._collapse_button.setObjectName("ai.collapse_button")
        self._collapse_button.setProperty("role", "ghost")
        self._collapse_button.setToolTip("Ciutkan panel AI")
        self._collapse_button.clicked.connect(self.toggle_collapsed)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self.status_label)
        head.addWidget(self._collapse_button)
        root.addLayout(head)

        self._body = QWidget()
        body = QVBoxLayout(self._body)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)

        intro = QLabel(
            "Bicara saja seperti biasa. AI memahami konteks chat dan membantu menyiapkan "
            "rencana download melalui perintah aplikasi yang aman."
        )
        intro.setProperty("muted", True)
        intro.setWordWrap(True)
        body.addWidget(intro)

        self.transcript = QTextBrowser()
        self.transcript.setObjectName("ai.transcript")
        self.transcript.setOpenExternalLinks(False)
        self.transcript.setPlaceholderText("Percakapan AI akan muncul di sini.")
        body.addWidget(self.transcript, 1)

        self.prompt = QTextEdit()
        self.prompt.setObjectName("ai_prompt")
        self.prompt.setPlaceholderText("Contoh: yang tadi ulang 720p tanpa subtitle…")
        self.prompt.setFixedHeight(88)
        body.addWidget(self.prompt)

        self.send_button = QPushButton("Kirim")
        self.send_button.setObjectName("ai.plan_button")
        self.send_button.setProperty("role", "primary")
        body.addWidget(self.send_button)
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

    def set_busy(self, busy: bool) -> None:
        self.send_button.setDisabled(busy)
        self.prompt.setDisabled(busy)
        self.set_status("Berpikir…" if busy else "Siap", success=not busy)

    def set_status(self, text: str, *, success: bool = False) -> None:
        self.status_label.setText(text)
        self.status_label.setProperty("badge", "success" if success else "warning")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def append_user_message(self, text: str) -> None:
        self._append_message("Kamu", text, user=True)

    def append_assistant_message(self, text: str) -> None:
        self._append_message("AI Agent", text, user=False)

    def clear_prompt(self) -> None:
        self.prompt.clear()

    def _append_message(self, label: str, text: str, *, user: bool) -> None:
        safe_label = escape(label)
        safe_text = escape(text).replace("\n", "<br>")
        align = "right" if user else "left"
        tone = "#2563EB" if user else "#111827"
        html = (
            f'<div style="margin:8px 0;text-align:{align};">'
            f'<div style="font-size:10px;color:#6B7280;">{safe_label}</div>'
            f'<div style="color:{tone};font-size:12px;line-height:1.35;">{safe_text}</div>'
            "</div>"
        )
        self.transcript.append(html)
        scrollbar = self.transcript.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
