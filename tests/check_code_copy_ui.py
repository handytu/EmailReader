"""Check the displayed and copied code using the reported X confirmation mail."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QPushButton
from app.models.message import MailMessage
from app.ui.main_window import MainWindow

app = QApplication([])
window = SimpleNamespace(code_card=QFrame(), code_value=QLabel(),
    copy_code_button=QPushButton('Copy code'), status_left=QLabel())
message = MailMessage('1', subject='Your X confirmation code is 040710',
    body_text='We noticed an attempt to login. Device 1355. Enter the following single-use code: 040710')
MainWindow._update_verification_code_card(window, message)
assert window.code_value.text() == '040710'
assert not window.code_card.isHidden()
MainWindow._copy_verification_code(window)
assert QApplication.clipboard().text() == '040710'
MainWindow._update_verification_code_card(window, MailMessage('2', subject='Login alert', body_text='Device 1355'))
assert window.current_verification_code == '' and window.code_card.isHidden()
print('PASS: card displays 040710, clipboard retains leading zero; ordinary alert hides code')
