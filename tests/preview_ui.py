"""Render the desktop layout with fictional data, without connecting to mail."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from app.models.account import EmailAccount, AccountState
from app.models.message import MailMessage
from app.ui.main_window import MainWindow
from app.ui.theme import QSS
from app.version import VERSION

app = QApplication([])
# The offscreen platform does not discover installed Windows fonts automatically.
for font in ("segoeui.ttf", "seguisb.ttf", "segoeuib.ttf", "consola.ttf", "calibri.ttf", "calibrib.ttf"):
    QFontDatabase.addApplicationFont(str(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / font))
app.setStyleSheet(QSS)
with patch.object(MainWindow, "_try_default_import"):
    window = MainWindow(None)
window.accounts = {
    "alex@example.com": EmailAccount("alex@example.com", provider="outlook", state=AccountState.CONNECTED, unread=2),
    "work@example.com": EmailAccount("work@example.com", provider="gmail", state=AccountState.CONNECTED, unread=1),
    "personal@example.com": EmailAccount("personal@example.com", provider="yahoo", state=AccountState.IDLE),
}
window.current_email = "alex@example.com"
window.messages = {window.current_email: [
    MailMessage("1", sender_name="Example Security", sender_addr="security@example.com",
                subject="Your verification code", preview="Use this code to finish signing in.",
                date=datetime.now(timezone.utc), to_addrs=["alex@example.com"],
                body_text="Your verification code is 654321.\n\nEnter it to finish signing in.\nThis code expires in 10 minutes.\n\nExample Security"),
    MailMessage("2", sender_name="Design Team", sender_addr="design@example.com",
                subject="Updated workspace designs", preview="The latest mockups are ready for review.", is_read=True),
    MailMessage("3", sender_name="Weekly Digest", sender_addr="digest@example.com",
                subject="Your weekly roundup", preview="Three things to catch up on this week.", is_starred=True),
]}
window._refresh_account_model()
window._refresh_mail_view()
window.mail_list.setCurrentIndex(window.mail_model.index(0, 0))
window.show()
assert window.windowTitle() == f"EmailReader v{VERSION}"
assert not window.windowIcon().isNull()
output = Path(__file__).resolve().parents[1] / "artifacts" / "ui-preview"
output.mkdir(parents=True, exist_ok=True)


def capture():
    for width, density in ((1440, "comfortable"), (1100, "compact")):
        window.resize(width, 880)
        window.mail_delegate.set_density(density)
        window.mail_list.doItemsLayout()
        app.processEvents()
        assert window.width() == width, (window.width(), width)
        assert all(button.width() >= button.minimumSizeHint().width()
                   for button in window.filter_buttons.values()), [(b.text(), b.width(), b.minimumSizeHint().width()) for b in window.filter_buttons.values()]
        assert window.star_button.accessibleName() == "Star message"
        assert window.current_message.uid == "1"
        assert window.grab().save(str(output / f"reader-{width}.png"))
    window._set_filter_mode("starred")
    assert window.filter_buttons["starred"].isChecked()
    assert not window.filter_buttons["all"].isChecked()
    assert window.current_message is None
    window.close()
    app.quit()
    print("Desktop layout checks passed; previews:", output)


def run_capture():
    try:
        capture()
    except Exception:
        import traceback
        traceback.print_exc()
        app.exit(1)


QTimer.singleShot(1200, run_capture)
sys.exit(app.exec())
