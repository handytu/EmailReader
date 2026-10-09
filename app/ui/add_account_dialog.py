from __future__ import annotations
import re
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QLabel, QDialogButtonBox, QGroupBox, QWidget, QSpinBox, QCheckBox)
from app.models.account import EmailAccount
from app.providers.detect import detect_provider


class AddAccountDialog(QDialog):
    def __init__(self, existing_keys=(), parent=None):
        super().__init__(parent)
        self.existing_keys = {key.lower() for key in existing_keys}
        self.account = None
        self.setWindowTitle("Add single account")
        self.setMinimumWidth(510)
        root = QVBoxLayout(self); root.setContentsMargins(20,20,20,20); root.setSpacing(12)
        title = QLabel("Add an email account")
        title.setStyleSheet("font-size:20px;font-weight:600;"); root.addWidget(title)
        hint = QLabel("Outlook can sign in with a Microsoft code without a password.\nFor Gmail/Yahoo, use your app password.")
        hint.setObjectName("muted"); hint.setWordWrap(True); root.addWidget(hint)
        form = QFormLayout()
        self.email = QLineEdit(); self.email.setPlaceholderText("you@example.com")
        self.password = QLineEdit(); self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Email",self.email); form.addRow("Password / app password",self.password)
        root.addLayout(form)
        group = QGroupBox("Advanced (optional)"); group.setCheckable(True); group.setChecked(False)
        self.advanced_group = group
        advanced_layout = QVBoxLayout(group)
        self.advanced = QWidget(); advanced = QFormLayout(self.advanced)
        self.refresh_token = QLineEdit(); self.refresh_token.setEchoMode(QLineEdit.Password)
        self.client_id = QLineEdit()
        self.proxy = QLineEdit(); self.proxy.setPlaceholderText("http://host:port")
        self.imap_host = QLineEdit(); self.imap_host.setPlaceholderText("Auto-detected when available")
        self.imap_port = QSpinBox(); self.imap_port.setRange(1,65535); self.imap_port.setValue(993)
        self.use_ssl = QCheckBox("Use SSL"); self.use_ssl.setChecked(True)
        for label,field in (("Microsoft refresh token",self.refresh_token),("Microsoft client ID",self.client_id),
                            ("Microsoft proxy",self.proxy),("IMAP host (other providers)",self.imap_host),
                            ("IMAP port",self.imap_port),("IMAP security",self.use_ssl)):
            advanced.addRow(label,field)
        advanced_layout.addWidget(self.advanced); self.advanced.hide()
        group.toggled.connect(self.advanced.setVisible); root.addWidget(group)
        self.error = QLabel(); self.error.setWordWrap(True)
        self.error.setStyleSheet("color:#F7A2AC;background:transparent;"); root.addWidget(self.error)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttons.button(QDialogButtonBox.Ok).setText("Add account")
        self.buttons.accepted.connect(self.accept); self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

    def accept(self):
        email = self.email.text().strip()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",email):
            self.error.setText("Enter a valid email address."); self.email.setFocus(); return
        if email.lower() in self.existing_keys:
            self.error.setText("This account is already added. Use Reconnect from its menu."); return
        provider,host,port = detect_provider(email)
        advanced = self.advanced_group.isChecked()
        custom_host = self.imap_host.text().strip() if advanced else ""
        password = self.password.text()
        if provider != "outlook" and not password:
            self.error.setText("Enter the password or app password for this account."); return
        if provider != "outlook" and not (custom_host or host):
            self.error.setText("Open Advanced and enter your IMAP host."); return
        self.account = EmailAccount(email=email,password=password,provider=provider,
            imap_host=custom_host or host, imap_port=self.imap_port.value() if custom_host else port,
            use_ssl=self.use_ssl.isChecked() if advanced else True,
            refresh_token=self.refresh_token.text().strip() if advanced else "",
            client_id=self.client_id.text().strip() if advanced else "",
            proxy=self.proxy.text().strip() if advanced else "")
        super().accept()
