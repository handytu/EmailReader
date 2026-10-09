"""Offline integration check for import, close, reopen and scheduled refresh."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from app.database.database import Database
from app.models.account import AccountState
from app.models.message import MailMessage
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow

app = QApplication([])
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / "import.txt"
    source.write_text("first@example.com|demo\nsession-demo@hotmail.com|demo", encoding="utf-8")
    def settings():
        service = SettingsService.__new__(SettingsService)
        service.path = root / "settings.json"
        return service
    with patch("app.ui.main_window.SettingsService", side_effect=settings), \
         patch("app.ui.main_window.app_dir", return_value=root), \
         patch.object(MainWindow, "_fetch") as fetch:
        window = MainWindow(Database(root / "mail.db"))
        window._load_file(source, quiet=True)
        window._worker_fetched("first@example.com", [MailMessage("1", body_text="First cached mail")])
        window._select_account("session-demo@hotmail.com")
        window._worker_fetched("session-demo@hotmail.com", [MailMessage("2", body_html="<p>Cached HTML</p>", body_text="Cached text")])
        window.close()
        source.unlink()
        restored = MainWindow(Database(root / "mail.db"))
        assert list(restored.accounts) == ["first@example.com", "session-demo@hotmail.com"]
        assert restored.current_email == "session-demo@hotmail.com"
        assert restored.messages["first@example.com"][0].body_text == "First cached mail"
        restored.mail_list.setCurrentIndex(restored.mail_model.index(0, 0))
        assert restored.current_message.body_html == "<p>Cached HTML</p>"
        assert restored.refresh_timer.isActive() and restored.refresh_timer.interval() == 10_000
        restored.accounts[restored.current_email].state = AccountState.CONNECTED
        fetch.reset_mock()
        restored.refresh_timer.timeout.emit()
        fetch.assert_called_once_with(restored.accounts[restored.current_email])
        restored.close()
        assert not restored.refresh_timer.isActive()
        app.processEvents()
print("PASS: import removed, reopen restored all accounts/full mail/last account; 10s timer targets current inbox")
