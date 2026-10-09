"""Process-isolated checks for Ctrl+W, graceful cancellation and stuck networking."""
import os
import sys
import subprocess
import time
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if len(sys.argv) == 1:
    for mode in ("idle", "cooperative", "stuck", "stuck-x"):
        started = time.monotonic()
        result = subprocess.run([sys.executable, __file__, mode], capture_output=True, text=True, timeout=8)
        elapsed = time.monotonic() - started
        assert result.returncode == 0, (mode, result.stdout, result.stderr)
        assert "CLOSE CHECK PASSED" in result.stdout, (mode, result.stdout, result.stderr)
        assert elapsed < 6, (mode, elapsed)
        print(f"PASS {mode}: exited in {elapsed:.2f}s")
    sys.exit(0)

from threading import Event
from unittest.mock import patch
from PySide6.QtCore import QThread, QTimer, QObject, Signal, Slot, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from app.ui.main_window import MainWindow

class FakeWorker(QObject):
    finished = Signal()
    def __init__(self, stuck):
        super().__init__()
        self.stuck = stuck
        self.stop = Event()
    def cancel(self):
        if not self.stuck:
            self.stop.set()
    @Slot()
    def run(self):
        self.stop.wait(30)
        self.finished.emit()

app = QApplication([])
with patch.object(MainWindow, "_try_default_import"):
    window = MainWindow(None)
window.show()
window.activateWindow()
window.search.setFocus()
if sys.argv[1] != "idle":
    thread = QThread(window)
    worker = FakeWorker(sys.argv[1].startswith("stuck"))
    worker.moveToThread(thread)
    window.threads.add(thread)
    window.workers.add(worker)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    thread.finished.connect(lambda: window.threads.discard(thread))
    thread.start()

def trigger():
    if sys.argv[1] == "stuck-x":
        window.close()
    else:
        QTest.keyClick(window.search, Qt.Key_W, Qt.ControlModifier)
    if not window._closing or window.isVisible() or window.refresh_timer.isActive():
        print("Close did not hide window/stop timer", flush=True)
        os._exit(1)
    print("CLOSE CHECK PASSED", flush=True)

QTimer.singleShot(250, trigger)
sys.exit(app.exec())
