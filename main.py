from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from app.version import APP_NAME, VERSION
from app.ui.main_window import MainWindow
from app.ui.theme import QSS
from app.database.database import Database
from app.utils.paths import app_dir, resource_path
from app.utils.logging_setup import setup_logging

def main():
    base = app_dir(); setup_logging(base)
    app = QApplication(sys.argv); app.setApplicationName(APP_NAME); app.setStyleSheet(QSS)
    app.setApplicationVersion(VERSION)
    app.setWindowIcon(QIcon(str(resource_path("resources/app-icon.ico"))))
    db = Database(base / "data" / "emailreader.db")
    win = MainWindow(db); win.show()
    raise SystemExit(app.exec())

if __name__ == "__main__": main()
