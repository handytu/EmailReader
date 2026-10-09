"""Verify startup has a dark native placeholder and switches to/from mail."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu')
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from app.ui.main_window import MainWindow
from app.ui.theme import QSS
from app.models.message import MailMessage

app = QApplication([])
app.setStyleSheet(QSS)
for name in ('segoeui.ttf', 'calibrib.ttf'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
with patch.object(MainWindow, '_try_default_import'):
    window = MainWindow(None)
window.resize(1440, 880)
window.show()
app.processEvents()
assert window.reader_stack.currentWidget() is window.empty_reader
assert not window.empty_reader.background.isNull()
image = window.empty_reader.grab().toImage()
assert image.pixelColor(5, 5).lightness() < 50
output = Path(__file__).resolve().parents[1] / 'artifacts/ui-preview/empty-reader-mountains.png'
window.grab().save(str(output))
window._render_message(MailMessage('1', body_text='Demo message'))
assert window.reader_stack.currentWidget() is window.viewer
window._show_empty_reader()
assert window.reader_stack.currentWidget() is window.empty_reader
window.resize(1100, 760)
app.processEvents()
assert window.empty_reader.width() > 0
window.close()
print('PASS: native dark startup, mountains asset, mail/empty transitions and narrow layout')
