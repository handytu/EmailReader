from __future__ import annotations
import html
import re
import os
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QSize, QUrl, QTimer
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QShortcut, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListView, QFileDialog, QMessageBox,
    QSplitter, QStatusBar, QMenu, QSizePolicy, QDialog, QStackedWidget
)


from PySide6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineSettings,
    QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo,
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from app.models.account import EmailAccount, AccountState
from app.version import APP_NAME, VERSION
from app.ui.title_bar import MountainTitleBar, WindowResizeFilter
from app.ui.brand_label import BrandLabel
from app.ui.empty_reader import EmptyReader
from app.ui.add_account_dialog import AddAccountDialog
from app.models.message import MailMessage
from app.email.code_extractor import extract_verification_code
from app.services.account_parser import parse_accounts_file
from app.workers.mail_worker import FetchWorker
from app.workers.action_worker import MailActionWorker
from app.database.database import Database
from app.utils.paths import app_dir, resource_path
from app.ui.settings_dialog import SettingsDialog
from app.ui.device_login_dialog import MicrosoftDeviceLoginDialog
from app.services.settings_service import SettingsService
from app.services.account_store import AccountStore
from app.ui.models import (
    AccountListModel, AccountDelegate, MailListModel, MailDelegate, MailRow,
    ROLE_KIND, ROLE_KEY, ROLE_ACCOUNT, ROLE_MESSAGE, ROLE_SOURCE_EMAIL
)

SCRIPT_RE = re.compile(r"<(script|iframe|object|embed|form)[^>]*>.*?</\1>|<(script|iframe|object|embed|form)[^>]*/?>", re.I | re.S)
EVENT_RE = re.compile(r"\son\w+\s*=\s*(['\"]).*?\1", re.I | re.S)
REMOTE_IMG_RE = re.compile(r"(<img\b[^>]*?\bsrc\s*=\s*)([\"\'])(https?://[^\"\']+)(\2)", re.I | re.S)
TRANSPARENT_PIXEL = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="


class EmailRequestInterceptor(QWebEngineUrlRequestInterceptor):
    """Blocks remote HTTP(S) resources until the user explicitly allows them."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.allow_remote = False

    def interceptRequest(self, info: QWebEngineUrlRequestInfo):
        url = info.requestUrl()
        if not self.allow_remote and url.scheme().lower() in {"http", "https"}:
            info.block(True)


class EmailWebPage(QWebEnginePage):
    """Open clicked web links in the system browser, never inside the mail viewer."""
    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame: bool) -> bool:
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            if url.scheme().lower() in {"http", "https", "mailto"}:
                QDesktopServices.openUrl(url)
            return False
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.accounts: dict[str, EmailAccount] = {}
        self.messages: dict[str, list[MailMessage]] = {}
        self.current_email = ""
        self.current_message: MailMessage | None = None
        self.current_source_email = ""
        self.current_verification_code = ""
        self.threads: set[QThread] = set()
        self.workers: set[FetchWorker] = set()
        self.action_threads: set[QThread] = set()
        self.action_workers: set[MailActionWorker] = set()
        self.fetching: set[str] = set()
        self.device_dialogs: dict[str, MicrosoftDeviceLoginDialog] = {}
        self.load_remote_images = False
        self.filter_mode = "all"
        self._action_buttons: list[QPushButton] = []
        self.settings_service = SettingsService()
        self.app_settings = self.settings_service.load()
        self.account_store = AccountStore(db.path.parent / "accounts.bin") if db else None
        self._closing = False

        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setWindowIcon(QIcon(str(resource_path("resources/app-icon.ico"))))
        self.resize(1440, 880)
        self.setMinimumSize(1100, 650)
        self._build_ui()
        self.resize_filter = WindowResizeFilter(self)
        QApplication.instance().installEventFilter(self.resize_filter)
        self.setMouseTracking(True)
        for widget in self.findChildren(QWidget):
            widget.setMouseTracking(True)
        for button in self.findChildren(QPushButton):
            button.setCursor(Qt.PointingHandCursor)
        for label in (self.subject, self.sender_name, self.sender_addr,
                      self.message_meta, self.inbox_account):
            label.setTextFormat(Qt.PlainText)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._bind_shortcuts()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(10_000)
        self.refresh_timer.timeout.connect(self._auto_refresh_current)
        self._try_default_import()
        if self.app_settings.auto_refresh:
            self.refresh_timer.start()

    # ---------- UI construction ----------
    def _icon(self, name: str) -> QIcon:
        p = resource_path(f"resources/icons/{name}.svg")
        return QIcon(str(p)) if p.exists() else QIcon()

    def _icon_button(self, icon: str, tooltip: str, slot=None) -> QPushButton:
        b = QPushButton(objectName="iconButton")
        b.setFixedSize(44, 44)
        b.setAccessibleName(tooltip)
        b.setCursor(Qt.PointingHandCursor)
        b.setIcon(self._icon(icon)); b.setIconSize(QSize(17, 17)); b.setToolTip(tooltip)
        if slot: b.clicked.connect(slot)
        return b

    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        self.title_bar = MountainTitleBar(self)
        outer.addWidget(self.title_bar)
        outer.addWidget(self._build_topbar())

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(self._build_sidebar())
        self.splitter.addWidget(self._build_mail_panel())
        self.splitter.addWidget(self._build_reader())
        self.splitter.setStretchFactor(0, 0); self.splitter.setStretchFactor(1, 0); self.splitter.setStretchFactor(2, 1)
        self.splitter.setSizes([280, 430, 730])
        outer.addWidget(self.splitter, 1)

        self.status = QStatusBar(); self.setStatusBar(self.status)
        self.status_left = QLabel("Offline", objectName="statusText")
        self.status_right = QLabel("0 accounts", objectName="statusText")
        self.status.addWidget(self.status_left, 1); self.status.addPermanentWidget(self.status_right)
        self._update_status_bar()

    def _build_topbar(self) -> QWidget:
        top = QFrame(objectName="topbar"); top.setFixedHeight(64)
        tl = QHBoxLayout(top); tl.setContentsMargins(14, 7, 14, 7); tl.setSpacing(10)
        self.brand = BrandLabel(self.app_settings.brand_email_color,self.app_settings.brand_reader_color)
        tl.addWidget(self.brand)
        tl.addStretch(1)
        self.global_search = QLineEdit(); self.global_search.setPlaceholderText("Search all accounts...")
        self.global_search.setFixedHeight(44); self.global_search.setMaximumWidth(440); self.global_search.setMinimumWidth(240)
        self.global_search.setAccessibleName("Search loaded messages across all accounts")
        self.global_search.textChanged.connect(self._global_search_changed); tl.addWidget(self.global_search)
        self.global_search.setClearButtonEnabled(True)
        self.global_search.setToolTip("Search messages already loaded across all accounts (Ctrl+Shift+F)")
        tl.addStretch(1)
        self.sync_button = self._icon_button("refresh-cw", "Sync current inbox (Ctrl+R)", self.refresh_current); tl.addWidget(self.sync_button)
        settings = self._icon_button("settings", "Settings", self._open_settings); tl.addWidget(settings)
        return top

    def _build_sidebar(self) -> QWidget:
        self.sidebar = QFrame(objectName="sidebar"); self.sidebar.setMinimumWidth(220); self.sidebar.setMaximumWidth(420)
        sl = QVBoxLayout(self.sidebar); sl.setContentsMargins(12, 12, 12, 8); sl.setSpacing(8)
        add = QPushButton("Add accounts", objectName="primary"); add.setIcon(self._icon("plus")); add.setIconSize(QSize(16, 16)); add.setFixedHeight(44); add.clicked.connect(self._add_accounts_menu); sl.addWidget(add)
        self.account_search = QLineEdit(); self.account_search.setPlaceholderText("Search accounts..."); self.account_search.setFixedHeight(44); self.account_search.setAccessibleName("Search accounts"); self.account_search.textChanged.connect(self._filter_accounts); sl.addWidget(self.account_search)
        section = QLabel("ACCOUNTS", objectName="sectionLabel"); sl.addWidget(section)

        self.account_model = AccountListModel(self)
        self.account_list = QListView(); self.account_list.setModel(self.account_model); self.account_list.setItemDelegate(AccountDelegate(self.account_list))
        self.account_list.setMouseTracking(True); self.account_list.setUniformItemSizes(False); self.account_list.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.account_list.setContextMenuPolicy(Qt.CustomContextMenu); self.account_list.customContextMenuRequested.connect(self._account_menu)
        self.account_list.clicked.connect(self._account_clicked)
        self.account_list.activated.connect(self._account_clicked)
        self.account_list.setAccessibleName("Email accounts — press Enter to open")
        sl.addWidget(self.account_list, 1)

        footer = QFrame(objectName="sidebarFooter"); fl = QHBoxLayout(footer); fl.setContentsMargins(2, 8, 2, 0); fl.setSpacing(6)
        self.connected_summary = QLabel("Connected 0 / 0", objectName="muted"); fl.addWidget(self.connected_summary); fl.addStretch(1)
        count = QLabel("0 accounts", objectName="muted"); self.account_count = count; fl.addWidget(count)
        sl.addWidget(footer)
        return self.sidebar

    def _build_mail_panel(self) -> QWidget:
        panel = QFrame(objectName="listPanel"); panel.setMinimumWidth(380); panel.setMaximumWidth(640)
        ml = QVBoxLayout(panel); ml.setContentsMargins(12, 12, 12, 8); ml.setSpacing(8)
        header = QHBoxLayout(); titles = QVBoxLayout(); titles.setSpacing(1)
        self.inbox_title = QLabel("Inbox", objectName="panelTitle"); titles.addWidget(self.inbox_title)
        self.inbox_account = QLabel("Select an account", objectName="muted"); titles.addWidget(self.inbox_account)
        header.addLayout(titles, 1)
        header.addWidget(self._icon_button("refresh-cw", "Refresh inbox", self.refresh_current))
        header.addWidget(self._icon_button("sliders-horizontal", "Filter messages", self._show_filter_menu))
        ml.addLayout(header)

        self.search = QLineEdit(); self.search.setPlaceholderText("Search in Inbox..."); self.search.setFixedHeight(44); self.search.setAccessibleName("Search current inbox"); self.search.textChanged.connect(self._local_search_changed); ml.addWidget(self.search)
        self.search.setClearButtonEnabled(True)
        self.account_search.setClearButtonEnabled(True)
        filter_row = QHBoxLayout(); filter_row.setSpacing(4); self.filter_buttons = {}
        for key, label in (("all", "All"), ("unread", "Unread"), ("starred", "Starred"), ("attachments", "Attachments")):
            b = QPushButton(label, objectName="segment"); b.setCheckable(True); b.setChecked(key == "all"); b.setProperty("active", key == "all"); b.clicked.connect(lambda checked=False, k=key: self._set_filter_mode(k)); filter_row.addWidget(b); self.filter_buttons[key] = b
            b.ensurePolished()
            b.setMinimumWidth(b.minimumSizeHint().width())
        filter_row.addStretch(1); ml.addLayout(filter_row)

        self.mail_model = MailListModel(self)
        self.mail_list = QListView(); self.mail_list.setModel(self.mail_model); self.mail_delegate = MailDelegate(self.mail_list, self.app_settings.density); self.mail_list.setItemDelegate(self.mail_delegate)
        self.mail_list.setMouseTracking(True); self.mail_list.setVerticalScrollMode(QListView.ScrollPerPixel); self.mail_list.setUniformItemSizes(True)
        self.mail_list.selectionModel().currentChanged.connect(self._mail_changed)
        self.mail_list.setContextMenuPolicy(Qt.CustomContextMenu); self.mail_list.customContextMenuRequested.connect(self._mail_menu)
        self.mail_list.setAccessibleName("Messages — use arrow keys to read")
        ml.addWidget(self.mail_list, 1)
        self.list_empty = QLabel("No messages loaded", objectName="muted"); self.list_empty.setAlignment(Qt.AlignCenter); self.list_empty.hide(); ml.addWidget(self.list_empty)
        return panel

    def _build_reader(self) -> QWidget:
        reader = QFrame(objectName="reader"); reader.setMinimumWidth(450)
        rl = QVBoxLayout(reader); rl.setContentsMargins(24, 20, 24, 12); rl.setSpacing(12)
        self.subject = QLabel("Select an email", objectName="subjectTitle"); self.subject.setWordWrap(True); rl.addWidget(self.subject)

        sender_row = QHBoxLayout(); sender_row.setSpacing(10)
        self.sender_avatar = QLabel(); self.sender_avatar.setFixedSize(36, 36); self.sender_avatar.setAlignment(Qt.AlignCenter); self.sender_avatar.setStyleSheet("background:#243A55;border-radius:18px;font-weight:600;"); sender_row.addWidget(self.sender_avatar)
        sender_text = QVBoxLayout(); sender_text.setSpacing(1)
        self.sender_name = QLabel("Choose a message from the list to read it.", objectName="senderName"); sender_text.addWidget(self.sender_name)
        self.sender_addr = QLabel("", objectName="muted"); sender_text.addWidget(self.sender_addr); sender_row.addLayout(sender_text, 1)
        self.reader_date = QLabel("", objectName="muted"); self.reader_date.setAlignment(Qt.AlignRight | Qt.AlignVCenter); sender_row.addWidget(self.reader_date)
        rl.addLayout(sender_row)
        self.message_meta = QLabel("", objectName="muted"); self.message_meta.setWordWrap(True); rl.addWidget(self.message_meta)

        # Gmail-style verification code card. It is shown only when a likely
        # OTP/login code is detected in the currently selected message.
        self.code_card = QFrame(objectName="codeCard")
        code_layout = QHBoxLayout(self.code_card); code_layout.setContentsMargins(14, 11, 12, 11); code_layout.setSpacing(12)
        code_copy = QVBoxLayout(); code_copy.setSpacing(2)
        self.code_title = QLabel("Verification code", objectName="codeTitle"); code_copy.addWidget(self.code_title)
        self.code_hint = QLabel("From this email", objectName="muted"); code_copy.addWidget(self.code_hint)
        code_layout.addLayout(code_copy, 1)
        self.code_value = QLabel("", objectName="codeValue"); self.code_value.setTextInteractionFlags(Qt.TextSelectableByMouse); code_layout.addWidget(self.code_value)
        self.copy_code_button = QPushButton("Copy code", objectName="codeCopyButton")
        self.copy_code_button.setIcon(self._icon("copy")); self.copy_code_button.setIconSize(QSize(15, 15)); self.copy_code_button.clicked.connect(self._copy_verification_code)
        code_layout.addWidget(self.copy_code_button)
        self.code_card.hide(); rl.addWidget(self.code_card)

        toolbar = QFrame(objectName="toolbar"); actions = QHBoxLayout(toolbar); actions.setContentsMargins(0, 2, 0, 2); actions.setSpacing(6)
        actions.addStretch(1)
        self.star_button = self._icon_button("star", "Star message", self._toggle_star_current); self.star_button.setCheckable(True); actions.addWidget(self.star_button)
        self.delete_button = self._icon_button("trash-2", "Delete message", self._delete_current); self.delete_button.setObjectName("dangerAction"); actions.addWidget(self.delete_button)
        self.more_button = self._icon_button("more-horizontal", "More message actions", self._show_more_menu); actions.addWidget(self.more_button)
        self._action_buttons.extend([self.star_button, self.delete_button, self.more_button])
        for b in self._action_buttons: b.setEnabled(False)
        rl.addWidget(toolbar)

        self.image_banner = QFrame(objectName="imageBanner"); ib = QHBoxLayout(self.image_banner); ib.setContentsMargins(12, 9, 12, 9)
        img = QLabel(); img.setPixmap(self._icon("image-off").pixmap(18, 18)); ib.addWidget(img)
        msg = QLabel("Remote images are blocked for your privacy.", objectName="secondary"); ib.addWidget(msg, 1)
        load = QPushButton("Load images"); load.clicked.connect(self._allow_remote_images); ib.addWidget(load)
        self.image_banner.hide(); rl.addWidget(self.image_banner)

        # QWebEngineView is used instead of QTextBrowser because modern HTML emails
        # (Discord, GitHub, newsletters, transactional mail) rely heavily on nested
        # tables and CSS that Qt rich-text does not render faithfully.
        self.web_profile = QWebEngineProfile(self)
        self.web_interceptor = EmailRequestInterceptor(self.web_profile)
        self.web_profile.setUrlRequestInterceptor(self.web_interceptor)
        self.web_page = EmailWebPage(self.web_profile, self)
        self.web_page.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, False)
        self.web_page.settings().setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, False)
        self.web_page.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, False)
        self.viewer = QWebEngineView()
        self.viewer.setPage(self.web_page)
        self.web_page.setBackgroundColor(QColor('#0B121B'))
        self.viewer.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.reader_stack = QStackedWidget()
        self.empty_reader = EmptyReader()
        self.reader_stack.addWidget(self.empty_reader)
        self.reader_stack.addWidget(self.viewer)
        rl.addWidget(self.reader_stack, 1)
        self._show_empty_reader()
        return reader

    def _open_settings(self):
        dialog = SettingsDialog(self.app_settings, self)
        if dialog.exec() != QDialog.Accepted:
            return
        self.app_settings = dialog.values()
        self.settings_service.save(self.app_settings)
        self.brand.set_colors(self.app_settings.brand_email_color,self.app_settings.brand_reader_color)
        if self.app_settings.auto_refresh:
            self.refresh_timer.start()
        else:
            self.refresh_timer.stop()
        self.mail_delegate.set_density(self.app_settings.density)
        self.mail_list.doItemsLayout()
        if self.current_message:
            self.load_remote_images = False
            self._render_message(self.current_message)
        self.status_left.setText("Settings saved")

    def _bind_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.refresh_current)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=lambda: self.search.setFocus())
        QShortcut(QKeySequence("Ctrl+Shift+F"), self, activated=lambda: self.global_search.setFocus())
        self.close_shortcut = QShortcut(QKeySequence("Ctrl+W"), self, activated=self.close)
        self.close_shortcut.setContext(Qt.ApplicationShortcut)

    # ---------- import/accounts ----------
    def _add_accounts_menu(self):
        menu = QMenu(self)
        imp = menu.addAction(self._icon("file-up"), "Import emails.txt")
        single = menu.addAction(self._icon("user-plus"), "Add single account")
        action = menu.exec(self.cursor().pos())
        if action == imp: self.import_accounts()
        elif action == single: self._add_single_account()

    def _add_single_account(self):
        dialog = AddAccountDialog(self.accounts,self)
        if dialog.exec() != QDialog.Accepted or dialog.account is None:
            return
        account = dialog.account
        self.accounts[account.email.lower()] = account
        self._save_accounts()
        self._restore_cached_messages()
        self._refresh_account_model()
        self._select_account(account.email.lower())

    def _try_default_import(self):
        if self.account_store and self.account_store.path.exists():
            try:
                self.accounts = self.account_store.load()
                self._restore_cached_messages()
                self._refresh_account_model()
                self._open_preferred_account()
            except Exception as error:
                QMessageBox.warning(self, "Session restore failed", f"Could not restore the saved session: {error}\nThe saved file has been preserved. Import your account file to reconnect.")
            return
        p = app_dir() / "emails.txt"
        if p.exists() and p.stat().st_size:
            self._load_file(p, quiet=True)

    def import_accounts(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Accounts", str(app_dir()), "Text files (*.txt);;All files (*.*)")
        if path: self._load_file(Path(path), quiet=False)

    def _load_file(self, path: Path, quiet: bool):
        try: report = parse_accounts_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Import failed", str(e)); return
        if not quiet:
            msg = f"Accounts found: {report.total_nonempty}\nValid: {len(report.accounts)}\nDuplicates: {report.duplicates}\nInvalid: {len(report.invalid)}\n\nImport {len(report.accounts)} accounts?"
            if QMessageBox.question(self, "Import Accounts", msg) != QMessageBox.Yes: return
        for account in report.accounts:
            self.accounts[account.email.lower()] = account
        self._save_accounts()
        self._restore_cached_messages()
        self._refresh_account_model()
        self._open_preferred_account()

    def _save_accounts(self):
        if self.account_store:
            try:
                self.account_store.save(self.accounts)
            except Exception as error:
                QMessageBox.warning(self, "Session save failed", f"Could not save accounts for next startup: {error}")

    def _restore_cached_messages(self):
        for account in self.accounts.values():
            if account.email not in self.messages:
                self.messages[account.email] = self.db.load_messages(account.email)
            account.unread = sum(not message.is_read for message in self.messages[account.email])

    def _open_preferred_account(self):
        if self.accounts and not self.current_email:
            preferred = self.app_settings.last_selected_account.lower() if self.app_settings.open_last_selected_account else ""
            if preferred and preferred in self.accounts:
                self._select_account(preferred)
            else:
                first = next(iter(self.accounts.values())); self._select_account(first.email.lower())

    def _refresh_account_model(self):
        selected = self.current_email.lower()
        self.account_model.set_accounts(self.accounts, selected)
        self._restore_account_selection(selected)
        self._update_status_bar()

    def _restore_account_selection(self, key: str):
        for row in range(self.account_model.rowCount()):
            idx = self.account_model.index(row, 0)
            if idx.data(ROLE_KEY) == key:
                self.account_list.setCurrentIndex(idx); return

    def _select_account(self, key: str):
        a = self.accounts.get(key)
        if not a: return
        self.current_email = a.email
        self.app_settings.last_selected_account = a.email
        self.settings_service.save(self.app_settings)
        self.inbox_title.setText("Inbox"); self.inbox_account.setText(a.email)
        self.load_remote_images = False
        self._show_empty_reader()
        self._show_messages(a.email)
        self._restore_account_selection(key)
        if self.messages.get(a.email):
            self.status_left.setText(f"{a.email}: Cached mail available")
        if a.state == AccountState.IDLE:
            self._fetch(a)

    def _auto_refresh_current(self):
        if self._closing or not self.app_settings.auto_refresh:
            return
        account = self.accounts.get(self.current_email.lower())
        if account and account.state == AccountState.CONNECTED and not self.action_threads:
            self._fetch(account)

    def closeEvent(self, event):
        self.refresh_timer.stop()
        if self._closing:
            event.ignore()
            return
        self._closing = True
        for dialog in list(self.device_dialogs.values()):
            dialog.close()
        if self.threads or self.action_threads:
            # Keep QObject/QThread owners alive until workers finish. Network calls
            # cannot always be interrupted, so bound shutdown of this process.
            event.ignore()
            QApplication.instance().setQuitOnLastWindowClosed(False)
            self.hide()
            for thread in (*self.threads, *self.action_threads):
                thread.requestInterruption()
            for worker in (*self.workers, *self.action_workers):
                worker.cancel()
            self._shutdown_deadline = time.monotonic() + 2.0
            QTimer.singleShot(50, self._finish_shutdown)
            return
        event.accept()

    def _finish_shutdown(self):
        if not self.threads and not self.action_threads:
            QApplication.instance().quit()
        elif time.monotonic() >= self._shutdown_deadline:
            # Avoid QThread destruction while native networking is still blocked.
            # Cache transactions run only on the UI thread and have already ended.
            os._exit(0)
        else:
            QTimer.singleShot(50, self._finish_shutdown)

    def _account_clicked(self, idx):
        kind = idx.data(ROLE_KIND); key = idx.data(ROLE_KEY)
        if kind == "group":
            self.account_model.toggle_group(key); return
        if kind == "all":
            self.current_email = "__all__"; self.inbox_title.setText("All Inboxes"); self.inbox_account.setText("All accounts")
            self._show_empty_reader()
            self._show_all_messages(); return
        if kind == "account": self._select_account(key)

    def _filter_accounts(self, text):
        self.account_model.set_filter(text)

    # ---------- fetching backend (preserved) ----------
    def refresh_current(self):
        if self.current_email == "__all__":
            return
        a = self.accounts.get(self.current_email.lower())
        if a: self._fetch(a)

    def _fetch(self, account: EmailAccount, force_device: bool = False):
        if self._closing:
            return
        key = account.email.lower()
        if key in self.fetching: return
        self.fetching.add(key); account.state = AccountState.CONNECTING
        self.account_model.refresh_account(key); self._update_status_bar(); self.status_left.setText(f"{account.email}: Connecting...")
        thread = QThread(self); worker = FetchWorker(account, self.app_settings.messages_per_load, force_device=force_device); worker.moveToThread(thread)
        self.threads.add(thread); self.workers.add(worker)
        thread.started.connect(worker.run); worker.status.connect(self._worker_status); worker.fetched.connect(self._worker_fetched)
        worker.device_login.connect(self._show_device_login)
        worker.finished.connect(thread.quit); worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda e=key: self.fetching.discard(e)); worker.finished.connect(lambda w=worker: self.workers.discard(w))
        thread.finished.connect(thread.deleteLater); thread.finished.connect(lambda t=thread: self.threads.discard(t)); thread.finished.connect(self._update_status_bar); thread.start()

    def _show_device_login(self, email_addr: str, verification_uri: str, user_code: str, message: str):
        if self._closing:
            return
        key = email_addr.lower()
        old = self.device_dialogs.pop(key, None)
        if old:
            old.close()
        dialog = MicrosoftDeviceLoginDialog(email_addr, verification_uri, user_code, message, self)
        self.device_dialogs[key] = dialog
        dialog.finished.connect(lambda _result, k=key: self.device_dialogs.pop(k, None))
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        # Device Code flow is explicitly interactive, so opening the official
        # Microsoft page here removes one manual step. The code stays visible.
        dialog.open_browser()

    def _worker_status(self, email_addr, state, detail):
        if self._closing:
            return
        key = email_addr.lower(); a = self.accounts.get(key)
        if not a: return
        try: a.state = AccountState(state)
        except ValueError: a.state = AccountState.ERROR
        a.error = detail if a.state not in (AccountState.CONNECTED, AccountState.CONNECTING) else ""
        dialog = self.device_dialogs.get(key)
        if dialog and a.state == AccountState.CONNECTED:
            dialog.set_connected()
            dialog.accept()
        elif dialog and a.state in (AccountState.AUTH_FAILED, AccountState.ERROR, AccountState.OFFLINE, AccountState.TIMEOUT):
            dialog.set_failed(detail)
        self.account_model.refresh_account(key); self._update_status_bar(); self.status_left.setText(f"{email_addr}: {detail}")

    def _worker_fetched(self, email_addr, messages):
        if self._closing:
            return
        if email_addr.lower() not in self.accounts:
            return
        self.messages[email_addr] = messages; self.db.cache_messages(email_addr, messages)
        a = self.accounts.get(email_addr.lower())
        if a: a.unread = sum(not m.is_read for m in messages)
        self._save_accounts()
        self.account_model.refresh_account(email_addr.lower()); self._update_status_bar()
        if self.global_search.text().strip(): self._refresh_mail_view()
        elif email_addr == self.current_email: self._show_messages(email_addr)
        elif self.current_email == "__all__": self._show_all_messages()
        self.status_left.setText(f"{email_addr} synced · {len(messages)} messages")

    # ---------- message list/reader ----------
    def _show_messages(self, email_addr: str):
        self._refresh_mail_view()

    def _show_all_messages(self):
        self._refresh_mail_view()

    def _refresh_mail_view(self):
        selected = (self.current_source_email, self.current_message.folder,
                    self.current_message.uid) if self.current_message else None
        query = self.global_search.text().strip()
        combined = bool(query) or self.current_email == "__all__"
        rows = []
        for source, messages in self.messages.items():
            if combined or source == self.current_email:
                rows.extend(MailRow(m, source, i) for i, m in enumerate(messages))
        if combined:
            rows.sort(key=lambda r: r.message.date.timestamp() if r.message.date else 0, reverse=True)
        self.inbox_title.setText("Search" if query else "All Inboxes" if combined else "Inbox")
        self.inbox_account.setText("Loaded accounts" if query else "All accounts" if combined else self.current_email or "Select an account")
        # Apply one model reset, then restore the selected message by mailbox identity.
        self.mail_model.filter_text = (query or self.search.text()).strip().casefold()
        self.mail_model.set_messages(rows)
        self._update_list_empty()
        for row_no, row in enumerate(self.mail_model.rows):
            if selected == (row.source_email, row.message.folder, row.message.uid):
                self.mail_list.setCurrentIndex(self.mail_model.index(row_no, 0))
                return
        self._show_empty_reader()

    def _mail_changed(self, cur, prev):
        if not cur.isValid(): return
        m: MailMessage = cur.data(ROLE_MESSAGE); source = cur.data(ROLE_SOURCE_EMAIL)
        if not m: return
        if self.current_message == m and self.current_source_email == source:
            self.current_message = m
            return
        self.current_message = m; self.current_source_email = source or self.current_email; self.load_remote_images = False
        for b in self._action_buttons: b.setEnabled(True)
        self.star_button.setToolTip("Unstar" if m.is_starred else "Star")
        self.star_button.setAccessibleName("Unstar message" if m.is_starred else "Star message")
        self.star_button.setChecked(m.is_starred)
        self.subject.setText(m.subject or "(No subject)")
        self.sender_name.setText(m.sender_name or m.sender_addr or "Unknown sender"); self.sender_addr.setText(m.sender_addr or "")
        self.sender_avatar.setText(((m.sender_name or m.sender_addr or "?")[:1]).upper())
        self.reader_date.setText(self._reader_date(m))
        source_hint = f" · {source}" if self.current_email == "__all__" else ""
        recipients = ", ".join(m.to_addrs) or "me"
        cc_hint = f" · Cc: {', '.join(m.cc_addrs)}" if m.cc_addrs else ""
        self.message_meta.setText(f"To: {recipients}{cc_hint}{source_hint}")
        self._update_verification_code_card(m)
        self._render_message(m)

    def _update_verification_code_card(self, m: MailMessage):
        code = extract_verification_code(m)
        self.current_verification_code = code or ""
        if not code:
            self.code_card.hide()
            return
        self.code_value.setText(code)
        self.code_card.show()

    def _copy_verification_code(self):
        if not self.current_verification_code:
            return
        QApplication.clipboard().setText(self.current_verification_code)
        self.copy_code_button.setText("Copied")
        self.status_left.setText("Verification code copied to clipboard")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1300, lambda: self.copy_code_button.setText("Copy code"))

    def _render_message(self, m: MailMessage):
        self.reader_stack.setCurrentWidget(self.viewer)
        self.image_banner.hide()
        self.web_interceptor.allow_remote = bool(self.load_remote_images or not self.app_settings.block_remote_images)

        if m.body_html:
            safe = SCRIPT_RE.sub("", m.body_html)
            safe = EVENT_RE.sub("", safe)

            # IMPORTANT: do not delete <img> tags. Many HTML emails use image
            # dimensions/spacer cells as part of their table layout. Removing the
            # whole tag can collapse a 600px template into a very narrow column
            # (this is especially visible in Discord transactional emails).
            has_remote = bool(REMOTE_IMG_RE.search(safe))
            if has_remote and self.app_settings.block_remote_images and not self.load_remote_images:
                safe = REMOTE_IMG_RE.sub(
                    lambda mt: f'{mt.group(1)}{mt.group(2)}{TRANSPARENT_PIXEL}{mt.group(4)}',
                    safe,
                )
                self.image_banner.show()

            # Keep the sender's HTML/CSS intact as much as possible. QWebEngine
            # handles table-based email layouts far more accurately than QTextBrowser.
            # The outer shell only supplies a neutral canvas and safe overflow rules.
            wrapped = f"""<!doctype html>
<html>
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<style>
html,body{{margin:0;padding:0;background:#F5F5F7;}}
body{{overflow-wrap:normal;word-break:normal;}}
img{{max-width:100%;}}
table{{max-width:100%;}}
.mail-shell{{box-sizing:border-box;width:100%;min-height:100%;padding:18px 16px 32px;overflow-x:auto;}}
</style>
</head>
<body><div class=\"mail-shell\">{safe}</div></body>
</html>"""
            self.viewer.setHtml(wrapped, QUrl("about:blank"))
        else:
            body = html.escape(m.body_text or m.preview or "")
            wrapped = f"""<!doctype html><html><head><meta charset=\"utf-8\"><style>
            html,body{{margin:0;background:#0B1119;color:#E7EDF5;font-family:'Segoe UI',Arial,sans-serif;font-size:14px;line-height:1.6;}}
            .plain{{box-sizing:border-box;max-width:900px;padding:18px 16px 32px;white-space:pre-wrap;overflow-wrap:anywhere;}}
            </style></head><body><div class=\"plain\">{body}</div></body></html>"""
            self.viewer.setHtml(wrapped, QUrl("about:blank"))

    def _allow_remote_images(self):
        if not self.current_message:
            return
        self.load_remote_images = True
        self.web_interceptor.allow_remote = True
        self._render_message(self.current_message)

    @staticmethod
    def _reader_date(m: MailMessage) -> str:
        if not m.date: return ""
        try: dt = m.date.astimezone()
        except Exception: dt = m.date
        return dt.strftime("%b %d, %Y\n%I:%M %p").replace(" 0", " ")

    def _show_empty_reader(self):
        self.current_message = None; self.current_source_email = ""; self.current_verification_code = ""; self.subject.setText("Select an email"); self.sender_avatar.setText("")
        for b in self._action_buttons: b.setEnabled(False)
        self.sender_name.setText("Choose a message from the list to read it."); self.sender_addr.setText(""); self.reader_date.setText(""); self.message_meta.setText("")
        self.code_card.hide(); self.image_banner.hide()
        self.reader_stack.setCurrentWidget(self.empty_reader)

    def _local_search_changed(self, text):
        self._refresh_mail_view()

    def _global_search_changed(self, text):
        self.search.setEnabled(not bool(text.strip()))
        self._refresh_mail_view()

    def _show_filter_menu(self):
        menu = QMenu(self)
        for key, button in self.filter_buttons.items():
            action = menu.addAction(button.text())
            action.setCheckable(True)
            action.setChecked(key == self.filter_mode)
            action.triggered.connect(lambda checked=False, mode=key: self._set_filter_mode(mode))
        menu.exec(self.cursor().pos())

    def _set_filter_mode(self, mode: str):
        self.filter_mode = mode; self.mail_model.mode = mode
        for key, button in self.filter_buttons.items():
            button.setChecked(key == mode)
            button.setProperty("active", key == mode); button.style().unpolish(button); button.style().polish(button)
        self._refresh_mail_view()

    def _update_list_empty(self):
        has_filter = bool(self.mail_model.filter_text) or self.filter_mode != "all"
        self.list_empty.setText("No messages match your search or filter" if has_filter else "No messages loaded — refresh this inbox to load mail" if self.current_email else "Select an account to load messages")
        self.list_empty.setVisible(self.mail_model.rowCount() == 0)
        self.mail_list.setVisible(self.mail_model.rowCount() > 0)

    # ---------- menus/status ----------
    def _account_menu(self, pos):
        idx = self.account_list.indexAt(pos)
        if not idx.isValid() or idx.data(ROLE_KIND) != "account": return
        key = idx.data(ROLE_KEY); a = self.accounts.get(key)
        if not a: return
        menu = QMenu(self)
        refresh = menu.addAction(self._icon("refresh-cw"), "Refresh")
        reconnect = menu.addAction(self._icon("plug"), "Reconnect")
        device_login = None
        if a.provider == "outlook":
            device_login = menu.addAction(self._icon("plug"), "Sign in with Microsoft code")
        copy = menu.addAction(self._icon("copy"), "Copy Email")
        menu.addSeparator(); settings = menu.addAction(self._icon("settings"), "Account Settings"); settings.setEnabled(False)
        remove = menu.addAction(self._icon("trash-2"), "Remove Account")
        action = menu.exec(self.account_list.viewport().mapToGlobal(pos))
        if action in (refresh, reconnect): self._fetch(a)
        elif device_login is not None and action == device_login: self._fetch(a, force_device=True)
        elif action == copy: QApplication.clipboard().setText(a.email)
        elif action == remove:
            self.accounts.pop(key, None)
            self.messages.pop(a.email, None)
            self._save_accounts()
            if self.current_email.lower() == key: self.current_email = ""; self._show_empty_reader(); self.mail_model.set_messages([])
            self._refresh_account_model()
            self._refresh_mail_view()

    def _mail_menu(self, pos):
        idx = self.mail_list.indexAt(pos)
        if not idx.isValid(): return
        self.mail_list.setCurrentIndex(idx)
        m: MailMessage = idx.data(ROLE_MESSAGE)
        menu = QMenu(self)
        open_action = menu.addAction("Open")
        menu.addSeparator()
        read_action = menu.addAction("Mark as Unread" if m.is_read else "Mark as Read")
        star_action = menu.addAction("Unstar" if m.is_starred else "Star")
        menu.addSeparator()
        delete_action = menu.addAction(self._icon("trash-2"), "Delete")
        action = menu.exec(self.mail_list.viewport().mapToGlobal(pos))
        if action == open_action: self.mail_list.setCurrentIndex(idx)
        elif action == read_action: self._set_read_current(not m.is_read)
        elif action == star_action: self._toggle_star_current()
        elif action == delete_action: self._delete_current()

    def _action_context(self):
        m = self.current_message
        source = self.current_source_email or self.current_email
        if not m or not source or source == "__all__":
            return None, None
        return self.accounts.get(source.lower()), m

    def _toggle_star_current(self):
        _, m = self._action_context()
        if not m: return
        self._run_mail_action("star", {"uid": m.uid, "value": not m.is_starred}, m)

    def _set_read_current(self, value: bool):
        _, m = self._action_context()
        if not m: return
        self._run_mail_action("read", {"uid": m.uid, "value": value}, m)

    def _delete_current(self):
        _, m = self._action_context()
        if not m: return
        if self.app_settings.confirm_delete:
            if QMessageBox.question(self, "Delete email", f"Delete ‘{m.subject}’?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
                return
        self._run_mail_action("delete", {"uid": m.uid}, m)

    def _show_more_menu(self):
        if not self.current_message: return
        m = self.current_message
        menu = QMenu(self)
        read_action = menu.addAction("Mark as Unread" if m.is_read else "Mark as Read")
        copy_sender = menu.addAction(self._icon("copy"), "Copy sender")
        copy_subject = menu.addAction(self._icon("copy"), "Copy subject")
        action = menu.exec(self.more_button.mapToGlobal(self.more_button.rect().bottomLeft()))
        if action == read_action: self._set_read_current(not m.is_read)
        elif action == copy_sender: QApplication.clipboard().setText(m.sender_addr or m.sender_name)
        elif action == copy_subject: QApplication.clipboard().setText(m.subject or "")

    def _run_mail_action(self, action: str, payload: dict, message: MailMessage | None = None):
        account, current = self._action_context()
        if not account:
            return
        target = message or current
        thread = QThread(self)
        worker = MailActionWorker(account, action, payload)
        worker.moveToThread(thread)
        self.action_threads.add(thread); self.action_workers.add(worker)
        for b in self._action_buttons: b.setEnabled(False)
        self.status_left.setText({"send":"Sending…", "star":"Updating star…", "read":"Updating message…", "delete":"Deleting…"}.get(action, "Working…"))
        thread.started.connect(worker.run)
        worker.succeeded.connect(lambda a, result, src=account.email, msg=target, pl=payload: self._mail_action_succeeded(a, result, src, msg, pl))
        worker.failed.connect(self._mail_action_failed)
        worker.finished.connect(thread.quit); worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda w=worker: self.action_workers.discard(w))
        thread.finished.connect(thread.deleteLater); thread.finished.connect(lambda t=thread: self.action_threads.discard(t))
        thread.finished.connect(lambda: [b.setEnabled(self.current_message is not None) for b in self._action_buttons])
        thread.start()

    def _mail_action_succeeded(self, action: str, result, source: str, m: MailMessage | None, payload: dict):
        if action == "send":
            self.status_left.setText("Message sent")
            return
        if not m:
            return
        if action == "star":
            m.is_starred = bool(payload.get("value"))
            self.status_left.setText("Star updated")
        elif action == "read":
            m.is_read = bool(payload.get("value")); self.status_left.setText("Read state updated")
        elif action == "delete":
            msgs = self.messages.get(source, [])
            self.messages[source] = [x for x in msgs if (x.folder, x.uid) != (m.folder, m.uid)]
            self.db.delete_message(source, m.folder, m.uid)
            self.status_left.setText("Email deleted")
            if self.current_source_email == source and self.current_message is m:
                self._show_empty_reader()
        if source in self.messages and action != "delete":
            self.db.cache_messages(source, self.messages[source])
        a = self.accounts.get(source.lower())
        if a:
            a.unread = sum(not x.is_read for x in self.messages.get(source, []))
            self.account_model.refresh_account(source.lower())
        if self.global_search.text().strip(): self._refresh_mail_view()
        elif self.current_email == "__all__": self._show_all_messages()
        elif self.current_email.lower() == source.lower(): self._show_messages(source)
        self._update_status_bar()

    def _mail_action_failed(self, action: str, error: str):
        if self._closing:
            return
        if self.current_message:
            self.star_button.setChecked(self.current_message.is_starred)
        self.status_left.setText(f"{action.title()} failed")
        QMessageBox.warning(self, f"{action.title()} failed", error)

    def _update_status_bar(self):
        total = len(self.accounts); connected = sum(a.state == AccountState.CONNECTED for a in self.accounts.values()); syncing = len(self.fetching)
        self.connected_summary.setText(f"Connected {connected} / {total}"); self.account_count.setText(f"{total} accounts")
        self.status_left.setText("Online" if total else "Offline")
        self.status_right.setText(f"{total} accounts" + (f" · {syncing} syncing" if syncing else ""))
