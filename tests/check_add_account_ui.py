"""Offline check: adding one account persists it and selects it for connection."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu')
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QFontDatabase
from app.database.database import Database
from app.services.settings_service import SettingsService, AppSettings
from app.ui.main_window import MainWindow
from app.ui.add_account_dialog import AddAccountDialog
from app.ui.settings_dialog import SettingsDialog
from app.ui.theme import QSS

app = QApplication([])
app.setStyleSheet(QSS)
for name in ('segoeui.ttf', 'calibrib.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
output = Path(__file__).resolve().parents[1] / 'artifacts/ui-preview'
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    def settings():
        service = object.__new__(SettingsService)
        service.path = root / 'settings.json'
        return service
    with patch('app.ui.main_window.SettingsService', side_effect=settings), \
         patch('app.ui.main_window.app_dir', return_value=root), \
         patch.object(MainWindow, '_fetch') as fetch:
        window = MainWindow(Database(root / 'mail.db'))
        def accept_form(dialog):
            dialog.email.setText('demo@hotmail.com')
            dialog.accept()
            return dialog.result()
        with patch.object(AddAccountDialog, 'exec', accept_form):
            window._add_single_account()
        assert window.current_email == 'demo@hotmail.com'
        fetch.assert_called_once_with(window.accounts['demo@hotmail.com'])
        assert 'demo@hotmail.com' in window.account_store.load()
        window.close()
        restored = MainWindow(Database(root / 'mail.db'))
        assert restored.current_email == 'demo@hotmail.com'
        restored.close()
for name, dialog in [('add-account', AddAccountDialog()), ('settings-colors', SettingsDialog(AppSettings()))]:
    if isinstance(dialog, AddAccountDialog):
        dialog.advanced_group.setChecked(True)
    dialog.show()
    app.processEvents()
    assert dialog.height() < 850, dialog.size()
    dialog.grab().save(str(output / (name + '.png')))
    dialog.close()
print('PASS: single account saved, selected and restored; dialog sizes checked')
