import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication, QDialog
from app.ui.add_account_dialog import AddAccountDialog
from app.ui.settings_dialog import SettingsDialog
from app.services.settings_service import AppSettings, SettingsService


class AddAccountTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_outlook_without_password_and_duplicate_rejected(self):
        dialog = AddAccountDialog()
        dialog.email.setText('demo@hotmail.com')
        dialog.accept()
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.account.provider, 'outlook')
        duplicate = AddAccountDialog(['DEMO@hotmail.com'])
        duplicate.email.setText('demo@hotmail.com')
        duplicate.accept()
        self.assertIsNone(duplicate.account)

    def test_password_and_custom_imap_validation(self):
        dialog = AddAccountDialog()
        dialog.email.setText('demo@example.com')
        dialog.accept()
        self.assertIsNone(dialog.account)
        dialog.password.setText('app|password')
        dialog.accept()
        self.assertIsNone(dialog.account)
        dialog.advanced_group.setChecked(True)
        dialog.imap_host.setText('imap.example.com')
        dialog.imap_port.setValue(143)
        dialog.use_ssl.setChecked(False)
        dialog.accept()
        self.assertEqual(dialog.account.password, 'app|password')
        self.assertEqual(dialog.account.imap_port, 143)
        self.assertFalse(dialog.account.use_ssl)

    def test_colors_persist_and_settings_cancel_does_not_mutate_original(self):
        original = AppSettings()
        dialog = SettingsDialog(original)
        dialog.brand_reader_color = '#aabbcc'
        self.assertEqual(original.brand_reader_color, '#629CFF')
        with tempfile.TemporaryDirectory() as directory:
            service = object.__new__(SettingsService)
            service.path = Path(directory) / 'settings.json'
            service.save(dialog.values())
            self.assertEqual(service.load().brand_reader_color, '#aabbcc')


if __name__ == '__main__':
    unittest.main()
