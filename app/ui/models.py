from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QFontMetrics
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem

from app.models.account import EmailAccount, AccountState
from app.models.message import MailMessage
from app.ui.theme import COLORS

ROLE_KIND = Qt.UserRole + 1
ROLE_KEY = Qt.UserRole + 2
ROLE_ACCOUNT = Qt.UserRole + 3
ROLE_MESSAGE = Qt.UserRole + 4
ROLE_SOURCE_EMAIL = Qt.UserRole + 5


def _stable_avatar_color(text: str) -> QColor:
    palette = ["#355C8A", "#496A4D", "#7A5148", "#66548D", "#3E6870", "#7B5B36", "#4C5D86", "#6B526D"]
    return QColor(palette[sum(ord(c) for c in text.lower()) % len(palette)])


def _status_color(state: AccountState) -> QColor:
    if state == AccountState.CONNECTED:
        return QColor(COLORS["success"])
    if state == AccountState.CONNECTING:
        return QColor(COLORS["warning"])
    if state in (AccountState.AUTH_FAILED, AccountState.ERROR, AccountState.TIMEOUT):
        return QColor(COLORS["error"])
    return QColor(COLORS["muted"])


@dataclass(slots=True)
class AccountRow:
    kind: str  # all | group | account
    key: str
    label: str
    count: int = 0
    account: EmailAccount | None = None


class AccountListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.accounts: dict[str, EmailAccount] = {}
        self.rows: list[AccountRow] = []
        self.filter_text = ""
        self.expanded_providers: set[str] = set()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.rows)):
            return None
        row = self.rows[index.row()]
        if role == ROLE_KIND:
            return row.kind
        if role == ROLE_KEY:
            return row.key
        if role == ROLE_ACCOUNT:
            return row.account
        if role == Qt.DisplayRole:
            return row.label
        if role == Qt.AccessibleTextRole:
            if row.account:
                return f"{row.account.email}, {row.account.state.value.replace('_', ' ').title()}, {row.account.unread} unread"
            return f"{row.label}, {row.count} unread"
        if role == Qt.ToolTipRole and row.account:
            detail = row.account.error or row.account.state.value.replace("_", " ").title()
            return f"{row.account.email}\n{row.account.provider.title()} · {detail}"
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        row = self.rows[index.row()]
        if row.kind == "group":
            return Qt.ItemIsEnabled
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def set_accounts(self, accounts: dict[str, EmailAccount], preserve_key: str = ""):
        self.accounts = accounts
        self._rebuild()

    def set_filter(self, text: str):
        self.filter_text = text.strip().lower()
        self._rebuild()

    def toggle_group(self, provider: str):
        provider = provider.lower()
        if provider in self.expanded_providers:
            self.expanded_providers.remove(provider)
        else:
            self.expanded_providers.add(provider)
        self._rebuild()

    def refresh_account(self, key: str):
        if self.rows and self.rows[0].kind == "all":
            self.rows[0].count = sum(a.unread for a in self.accounts.values())
            idx = self.index(0, 0)
            self.dataChanged.emit(idx, idx, [Qt.DisplayRole])
        for row_no, row in enumerate(self.rows):
            if row.kind == "account" and row.key == key:
                idx = self.index(row_no, 0)
                self.dataChanged.emit(idx, idx, [Qt.DisplayRole, Qt.ToolTipRole])
                return
        self._rebuild()

    def _rebuild(self):
        self.beginResetModel()
        rows: list[AccountRow] = [AccountRow("all", "__all__", "All Inboxes", sum(a.unread for a in self.accounts.values()))]
        # IMPORTANT: dict insertion order mirrors the order in emails.txt.
        # Do not sort/group here; users expect the sidebar and sequential loading
        # order to match the source file exactly.
        values = [a for a in self.accounts.values() if not self.filter_text or self.filter_text in a.email.lower() or self.filter_text in a.provider.lower()]
        rows.extend(AccountRow("account", a.email.lower(), a.email, account=a) for a in values)
        self.rows = rows
        self.endResetModel()


class AccountDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        kind = index.data(ROLE_KIND)
        return QSize(0, 48 if kind in ("all", "group") else 64)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        r = option.rect.adjusted(4, 2, -4, -2)
        kind = index.data(ROLE_KIND)
        selected = bool(option.state & QStyle.State_Selected)
        hover = bool(option.state & QStyle.State_MouseOver)
        if selected:
            painter.setBrush(QColor("#192A3D")); painter.setPen(Qt.NoPen); painter.drawRoundedRect(r, 8, 8)
            painter.setBrush(QColor(COLORS["primary"])); painter.drawRoundedRect(r.left(), r.top()+5, 3, r.height()-10, 1.5, 1.5)
        elif hover:
            painter.setBrush(QColor("#162333")); painter.setPen(Qt.NoPen); painter.drawRoundedRect(r, 8, 8)

        if kind == "all":
            painter.setPen(QColor(COLORS["text"])); f = painter.font(); f.setWeight(QFont.DemiBold); painter.setFont(f)
            painter.drawText(r.adjusted(13, 0, -44, 0), Qt.AlignVCenter | Qt.AlignLeft, "All Inboxes")
            count = self._row(index).count
            if count:
                badge = r.adjusted(r.width()-43, 9, -8, -9)
                painter.setBrush(QColor("#243A55")); painter.setPen(Qt.NoPen); painter.drawRoundedRect(badge, 9, 9)
                painter.setPen(QColor(COLORS["secondary"])); painter.drawText(badge, Qt.AlignCenter, str(count))
        elif kind == "group":
            row = self._row(index)
            painter.setPen(QColor(COLORS["secondary"])); f = painter.font(); f.setWeight(QFont.DemiBold); painter.setFont(f)
            painter.drawText(r.adjusted(13, 0, -42, 0), Qt.AlignVCenter | Qt.AlignLeft, row.label)
            painter.setPen(QColor(COLORS["muted"])); painter.drawText(r.adjusted(r.width()-40, 0, -10, 0), Qt.AlignVCenter | Qt.AlignRight, str(row.count))
        else:
            a: EmailAccount = index.data(ROLE_ACCOUNT)
            if not a:
                painter.restore(); return
            avatar = r.adjusted(10, 11, -(r.width()-42), -11)
            painter.setBrush(_stable_avatar_color(a.email)); painter.setPen(Qt.NoPen); painter.drawEllipse(avatar)
            painter.setPen(QColor("#F1F5F9")); af = painter.font(); af.setWeight(QFont.DemiBold); painter.setFont(af)
            painter.drawText(avatar, Qt.AlignCenter, (a.email[:1] or "?").upper())

            text_x = avatar.right() + 10
            status_space = 23
            email_rect = r.adjusted(text_x-r.left(), 8, -status_space, -(r.height()//2))
            provider_rect = r.adjusted(text_x-r.left(), r.height()//2, -status_space, -6)
            fm = QFontMetrics(painter.font())
            painter.setPen(QColor(COLORS["text"])); painter.drawText(email_rect, Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(a.email, Qt.ElideRight, email_rect.width()))
            pf = painter.font(); pf.setPointSize(max(8, pf.pointSize()-1)); pf.setWeight(QFont.Normal); painter.setFont(pf)
            status = a.state.value.replace("_", " ").title()
            detail = f"{a.provider.title()} · {status}"
            if a.unread:
                detail += f" · {a.unread} unread"
            painter.setPen(QColor(COLORS["muted"])); painter.drawText(provider_rect, Qt.AlignLeft | Qt.AlignVCenter, QFontMetrics(pf).elidedText(detail, Qt.ElideRight, provider_rect.width()))
            painter.setBrush(_status_color(a.state)); painter.setPen(Qt.NoPen); painter.drawEllipse(r.right()-16, r.center().y()-4, 8, 8)
        if option.state & QStyle.State_HasFocus:
            painter.setBrush(Qt.NoBrush); painter.setPen(QPen(QColor("#91BAFF"), 1, Qt.DashLine)); painter.drawRoundedRect(r, 8, 8)
        painter.restore()

    @staticmethod
    def _row(index: QModelIndex) -> AccountRow:
        model: AccountListModel = index.model()
        return model.rows[index.row()]


@dataclass(slots=True)
class MailRow:
    message: MailMessage
    source_email: str
    source_index: int


class MailListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.source: list[MailRow] = []
        self.rows: list[MailRow] = []
        self.filter_text = ""
        self.mode = "all"

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self.rows)):
            return None
        row = self.rows[index.row()]
        if role == ROLE_MESSAGE: return row.message
        if role == ROLE_SOURCE_EMAIL: return row.source_email
        if role == ROLE_KEY: return row.source_index
        if role == Qt.AccessibleTextRole:
            state = "Read" if row.message.is_read else "Unread"
            return f"{state}, {row.message.sender_name or row.message.sender_addr}, {row.message.subject}"
        if role == Qt.ToolTipRole: return row.message.subject
        return None

    def set_messages(self, messages: list[MailRow]):
        self.source = messages
        self._apply()

    def set_filter(self, text: str):
        self.filter_text = text.strip().casefold(); self._apply()

    def set_mode(self, mode: str):
        self.mode = mode; self._apply()

    def _apply(self):
        t = self.filter_text
        def keep(row: MailRow):
            m = row.message
            if self.mode == "unread" and m.is_read: return False
            if self.mode == "starred" and not m.is_starred: return False
            if self.mode == "attachments" and not m.attachments: return False
            if not t: return True
            hay = " ".join((row.source_email, m.sender_name, m.sender_addr,
                            m.subject, m.preview, m.body_text,
                            " ".join(m.to_addrs), " ".join(m.cc_addrs))).casefold()
            return t in hay
        self.beginResetModel(); self.rows = [r for r in self.source if keep(r)]; self.endResetModel()


class MailDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, density: str = "comfortable"):
        super().__init__(parent)
        self.density = density

    def set_density(self, density: str):
        self.density = density

    def sizeHint(self, option, index):
        return QSize(0, 72 if self.density == "compact" else 96)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save(); painter.setRenderHint(QPainter.Antialiasing)
        row: MailRow = index.model().rows[index.row()]
        m = row.message
        r = option.rect.adjusted(4, 2, -4, -2)
        selected = bool(option.state & QStyle.State_Selected); hover = bool(option.state & QStyle.State_MouseOver)
        if selected:
            painter.setBrush(QColor("#192A3D")); painter.setPen(Qt.NoPen); painter.drawRoundedRect(r, 8, 8)
            painter.setBrush(QColor(COLORS["primary"])); painter.drawRoundedRect(r.left(), r.top()+5, 3, r.height()-10, 1.5, 1.5)
        elif hover:
            painter.setBrush(QColor("#162333")); painter.setPen(Qt.NoPen); painter.drawRoundedRect(r, 8, 8)

        x = r.left()+14
        if not m.is_read:
            painter.setBrush(QColor(COLORS["primary"])); painter.setPen(Qt.NoPen); painter.drawEllipse(r.left()+6, r.top()+16, 6, 6)
        usable = r.right()-x-12
        sender_rect = r.adjusted(x-r.left(), 8, -72, -(r.height()-27))
        time_rect = r.adjusted(r.width()-76, 8, -12, -(r.height()-27))
        subject_rect = r.adjusted(x-r.left(), 31, -12, -(r.height()-51))
        preview_rect = r.adjusted(x-r.left(), 54, -12, -8)
        f = painter.font(); f.setWeight(QFont.DemiBold if not m.is_read else QFont.Medium); painter.setFont(f)
        painter.setPen(QColor(COLORS["text"])); fm = QFontMetrics(f)
        sender = m.sender_name or m.sender_addr or "Unknown sender"
        painter.drawText(sender_rect, Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(sender, Qt.ElideRight, sender_rect.width()))
        tf = painter.font(); tf.setPointSize(max(8, tf.pointSize()-1)); tf.setWeight(QFont.Normal); painter.setFont(tf)
        painter.setPen(QColor(COLORS["muted"])); painter.drawText(time_rect, Qt.AlignRight | Qt.AlignVCenter, _compact_date(m.date))
        sf = painter.font(); sf.setPointSize(sf.pointSize()+1); sf.setWeight(QFont.DemiBold if not m.is_read else QFont.Medium); painter.setFont(sf)
        painter.setPen(QColor(COLORS["text"])); sfm = QFontMetrics(sf); painter.drawText(subject_rect, Qt.AlignLeft | Qt.AlignVCenter, sfm.elidedText(m.subject or "(No subject)", Qt.ElideRight, subject_rect.width()))
        pf = painter.font(); pf.setPointSize(max(8, pf.pointSize()-1)); pf.setWeight(QFont.Normal); painter.setFont(pf)
        if self.density != "compact":
            painter.setPen(QColor(COLORS["muted"])); pfm = QFontMetrics(pf); painter.drawText(preview_rect, Qt.AlignLeft | Qt.AlignVCenter, pfm.elidedText(m.preview or "", Qt.ElideRight, preview_rect.width()))
        if option.state & QStyle.State_HasFocus:
            painter.setBrush(Qt.NoBrush); painter.setPen(QPen(QColor("#91BAFF"), 1, Qt.DashLine)); painter.drawRoundedRect(r, 8, 8)
        painter.restore()


def _compact_date(dt: datetime | None) -> str:
    if not dt: return ""
    try:
        local = dt.astimezone()
    except Exception:
        local = dt
    now = datetime.now(local.tzinfo) if local.tzinfo else datetime.now()
    if local.date() == now.date(): return local.strftime("%H:%M")
    delta = (now.date() - local.date()).days
    if delta == 1: return "Yesterday"
    if 1 < delta < 7: return local.strftime("%a")
    return local.strftime("%b %d")
