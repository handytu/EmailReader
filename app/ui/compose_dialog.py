from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton,
)


class ComposeDialog(QDialog):
    def __init__(self, parent=None, *, title="Compose", to="", cc="", subject="", body=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(680, 520)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel("To"))
        self.to_edit = QLineEdit(to)
        self.to_edit.setPlaceholderText("recipient@example.com")
        layout.addWidget(self.to_edit)

        layout.addWidget(QLabel("Cc"))
        self.cc_edit = QLineEdit(cc)
        self.cc_edit.setPlaceholderText("optional")
        layout.addWidget(self.cc_edit)

        layout.addWidget(QLabel("Subject"))
        self.subject_edit = QLineEdit(subject)
        layout.addWidget(self.subject_edit)

        layout.addWidget(QLabel("Message"))
        self.body_edit = QTextEdit()
        self.body_edit.setPlainText(body)
        layout.addWidget(self.body_edit, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.send_button = QPushButton("Send", objectName="primary")
        self.send_button.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(self.send_button)
        layout.addLayout(buttons)

    @staticmethod
    def _split_addresses(value: str) -> list[str]:
        return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]

    def values(self) -> dict:
        return {
            "to": self._split_addresses(self.to_edit.text()),
            "cc": self._split_addresses(self.cc_edit.text()),
            "subject": self.subject_edit.text().strip(),
            "body": self.body_edit.toPlainText(),
        }
