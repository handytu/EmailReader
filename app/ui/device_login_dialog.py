from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
)


class MicrosoftDeviceLoginDialog(QDialog):
    """Small non-blocking dialog for Microsoft Device Code authentication."""

    def __init__(self, account_email: str, verification_uri: str, user_code: str, message: str = "", parent=None):
        super().__init__(parent)
        self.account_email = account_email
        self.verification_uri = verification_uri or "https://www.microsoft.com/link"
        self.user_code = user_code

        self.setWindowTitle("Microsoft sign in")
        self.setModal(False)
        self.setMinimumWidth(470)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        title = QLabel("Sign in to Microsoft")
        f = QFont(title.font())
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        root.addWidget(title)

        account = QLabel(account_email)
        account.setObjectName("muted")
        root.addWidget(account)

        hint = QLabel("Open the Microsoft sign-in page and enter this code:")
        hint.setWordWrap(True)
        root.addWidget(hint)

        code = QLabel(user_code)
        code.setTextInteractionFlags(Qt.TextSelectableByMouse)
        code.setAlignment(Qt.AlignCenter)
        code.setStyleSheet(
            "QLabel { background:#101A26; border:1px solid #243244; border-radius:8px; "
            "padding:14px; font-size:24px; font-weight:700; letter-spacing:3px; }"
        )
        root.addWidget(code)

        if message:
            msg = QLabel(message)
            msg.setWordWrap(True)
            msg.setObjectName("muted")
            root.addWidget(msg)

        self.status = QLabel("Waiting for authentication…")
        self.status.setObjectName("muted")
        root.addWidget(self.status)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        copy_btn = QPushButton("Copy code")
        open_btn = QPushButton("Open Microsoft")
        open_btn.setObjectName("primary")
        copy_btn.clicked.connect(self.copy_code)
        open_btn.clicked.connect(self.open_browser)
        buttons.addWidget(copy_btn)
        buttons.addWidget(open_btn)
        root.addLayout(buttons)

    def copy_code(self):
        QApplication.clipboard().setText(self.user_code)
        self.status.setText("Code copied. Waiting for authentication…")

    def open_browser(self):
        QDesktopServices.openUrl(QUrl(self.verification_uri))
        self.status.setText("Browser opened. Complete sign-in, then return to EmailReader.")

    def set_connected(self):
        self.status.setText("Signed in successfully.")

    def set_failed(self, detail: str):
        self.status.setText(detail or "Sign-in failed.")
