import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS","--disable-gpu")
import sys
from pathlib import Path
from unittest.mock import patch, Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from app.ui.main_window import MainWindow

app = QApplication([])
with patch.object(MainWindow,"_try_default_import"):
    window = MainWindow(None)
window.show(); app.processEvents()
bar = window.title_bar
assert not bar.background.isNull()
assert window.windowFlags() & Qt.FramelessWindowHint
assert window.resize_filter.edges_at(QPoint(0,0)) == Qt.TopEdge|Qt.LeftEdge
assert window.resize_filter.edges_at(QPoint(window.width()-1,window.height()-1)) == Qt.BottomEdge|Qt.RightEdge
assert not window.resize_filter.edges_at(QPoint(100,100))
QTest.mouseClick(bar.maximize,Qt.LeftButton); app.processEvents()
assert window.isMaximized()
assert bar.maximize.accessibleName() == "Restore"
assert not window.resize_filter.edges_at(QPoint(0,0))
QTest.mouseClick(bar.maximize,Qt.LeftButton); app.processEvents()
assert not window.isMaximized()
QTest.mouseDClick(bar,Qt.LeftButton,pos=QPoint(350,20)); app.processEvents()
assert window.isMaximized()
bar.toggle_maximized(); app.processEvents()
handle = Mock()
with patch.object(window,"windowHandle",return_value=handle):
    QTest.mousePress(bar,Qt.LeftButton,pos=QPoint(350,20))
    handle.startSystemMove.assert_called_once()
QTest.mouseClick(bar.minimize,Qt.LeftButton); app.processEvents()
assert window.isMinimized()
window.showNormal(); app.processEvents()
QTest.mouseClick(bar.close_button,Qt.LeftButton); app.processEvents()
assert window._closing and not window.isVisible()
print("PASS: background, frameless window, edge resizing, maximize/restore, double-click, drag dispatch, minimize, close")
