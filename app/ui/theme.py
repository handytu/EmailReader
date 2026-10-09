from __future__ import annotations

# EmailReader 2026 design tokens. Keep visual decisions centralized here.
COLORS = {
    "bg_app": "#090F16",
    "topbar": "#0D151F",
    "sidebar": "#0D141D",
    "mail_list": "#101822",
    "reader": "#0B1119",
    "card": "#121C28",
    "hover": "#162333",
    "selected": "#192A3D",
    "border": "#1F2C3C",
    "primary": "#4D8DFF",
    "primary_hover": "#639CFF",
    "text": "#F1F5F9",
    "secondary": "#B0BBC8",
    "muted": "#9AA9BC",
    "success": "#3ECF78",
    "warning": "#E9A23B",
    "error": "#F05F6D",
}

QSS = r'''
* {
    font-family: "Segoe UI";
    font-size: 14px;
    color: #F1F5F9;
}
QMainWindow, QWidget { background: #090F16; }
QLabel { background: transparent; }
QFrame#topbar { background: #0D151F; border-bottom: 1px solid #1F2C3C; }
QFrame#sidebar { background: #0D141D; }
QFrame#listPanel { background: #101822; }
QFrame#reader { background: #0B1119; }
QFrame#readerHeader { background: transparent; }
QFrame#toolbar { background: transparent; }
QFrame#imageBanner { background: #121C28; border: 1px solid #1F2C3C; border-radius: 8px; }
QFrame#sidebarFooter { background: transparent; border-top: 1px solid #172434; }

QLabel#brand { font-size: 18px; font-weight: 600; }
QLabel#panelTitle { font-size: 20px; font-weight: 600; }
QLabel#subjectTitle { font-size: 24px; font-weight: 600; }
QLabel#senderName { font-size: 14px; font-weight: 600; }
QLabel#muted { color: #9AA9BC; }
QLabel#secondary { color: #B0BBC8; }
QLabel#sectionLabel { color: #9AA9BC; font-size: 12px; font-weight: 600; }
QLabel#statusText { color: #B0BBC8; font-size: 12px; }

QLineEdit {
    background: #101A26;
    border: 1px solid #243244;
    border-radius: 7px;
    padding: 7px 10px;
    color: #F1F5F9;
    selection-background-color: #4D8DFF;
}
QLineEdit:hover { border-color: #314157; }
QLineEdit:focus { border: 1px solid #4D8DFF; }
QLineEdit::placeholder { color: #9AA9BC; }
QLineEdit:disabled { color: #9AA9BC; background: #0D151F; }

QPushButton {
    min-height: 42px;
    background: #121C28;
    border: 1px solid #243244;
    border-radius: 7px;
    padding: 0 11px;
}
QPushButton:hover { background: #162333; border-color: #314157; }
QPushButton:pressed { background: #192A3D; }
QPushButton:focus { border: 1px solid #91BAFF; }
QPushButton:disabled { color: #566476; background: #101822; border-color: #1A2735; }
QPushButton#primary { background: #4D8DFF; border-color: #4D8DFF; color: #090F16; font-weight: 600; }
QPushButton#primary:hover { background: #639CFF; border-color: #639CFF; }
QPushButton#iconButton, QPushButton#dangerAction { min-width: 42px; max-width: 42px; padding: 0; background: transparent; border-color: transparent; }
QPushButton#iconButton:hover { background: #162333; }
QPushButton#iconButton:checked { background: #192A3D; border-color: #4D8DFF; }
QPushButton#iconButton:focus, QPushButton#dangerAction:focus { border-color: #91BAFF; }
QPushButton#toolAction { background: #121C28; }
QPushButton#dangerAction:hover { background: #321A22; border-color: #6B2A38; color: #F7B5BE; }
QPushButton#segment { min-height: 42px; padding: 0 7px; font-size: 12px; background: transparent; border-color: transparent; color: #B0BBC8; }
QPushButton#segment:hover { background: #162333; color: #F1F5F9; }
QPushButton#segment[active="true"] { background: #192A3D; border-color: #355C8A; color: #F1F5F9; font-weight: 600; }
QPushButton#segment:focus { border-color: #91BAFF; }

QListView, QListWidget {
    background: transparent;
    border: none;
    outline: none;
    selection-background-color: transparent;
}
QListView::item, QListWidget::item { border: none; }
QListView:focus { border: 1px solid #355C8A; border-radius: 7px; }

QTextBrowser {
    background: #0B1119;
    border: none;
    padding: 0;
    color: #F1F5F9;
}

QSplitter::handle { background: #1D2937; width: 4px; }
QSplitter::handle:hover { background: #35465B; }

QScrollBar:vertical { background: transparent; width: 6px; margin: 0; }
QScrollBar::handle:vertical { background: #314157; border-radius: 3px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #41546F; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 6px; }
QScrollBar::handle:horizontal { background: #314157; border-radius: 3px; min-width: 28px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QStatusBar { background: #0D151F; color: #778597; border-top: 1px solid #1F2C3C; min-height: 24px; max-height: 26px; }
QStatusBar::item { border: none; }

QMenu { background: #121C28; border: 1px solid #243244; border-radius: 7px; padding: 5px; }
QMenu::item { padding: 7px 26px 7px 10px; border-radius: 5px; }
QMenu::item:selected { background: #192A3D; }
QMenu::separator { height: 1px; background: #243244; margin: 5px 7px; }

QToolTip { background: #1A2431; color: #E7EDF5; border: 1px solid #314157; padding: 6px 8px; }
'''

# Verification-code card (Gmail-inspired convenience feature, adapted to EmailReader).
QSS += r'''
QFrame#codeCard {
    background: #111D2A;
    border: 1px solid #26384D;
    border-radius: 9px;
}
QLabel#codeTitle {
    color: #DCE7F5;
    font-size: 12px;
    font-weight: 600;
}
QLabel#codeValue {
    color: #F4F8FD;
    font-family: "Consolas";
    font-size: 22px;
    font-weight: 600;
    padding: 4px 8px;
}
QPushButton#codeCopyButton {
    min-height: 42px;
    background: #173A5B;
    border: 1px solid #24547D;
    color: #EAF4FF;
    font-weight: 600;
}
QPushButton#codeCopyButton:hover {
    background: #1D4B76;
    border-color: #316A9D;
}
'''

QSS += r'''
QDialog { background: #0B1119; }
QComboBox {
    min-height: 32px;
    background: #101A26;
    border: 1px solid #243244;
    border-radius: 7px;
    padding: 0 10px;
    color: #F1F5F9;
}
QComboBox:hover { border-color: #314157; }
QComboBox:focus { border-color: #4D8DFF; }
QComboBox QAbstractItemView {
    background: #121C28;
    border: 1px solid #243244;
    selection-background-color: #192A3D;
    color: #F1F5F9;
}
QCheckBox { spacing: 8px; min-height: 32px; color: #DCE5EF; }
QCheckBox:focus { color: #91BAFF; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #41546F;
    border-radius: 4px;
    background: #101A26;
}
QCheckBox::indicator:checked {
    background: #4D8DFF;
    border-color: #4D8DFF;
}
QDialogButtonBox QPushButton { min-width: 82px; }
'''
