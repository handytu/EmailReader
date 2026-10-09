from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QColor


class BrandLabel(QLabel):
    """The approved Calibri Bold wordmark with independently editable colors."""
    def __init__(self, email_color="#F1F5F9", reader_color="#629CFF", parent=None):
        super().__init__(parent)
        self.setAccessibleName("EmailReader")
        self.setStyleSheet('background:transparent;font-family:"Calibri";font-size:23px;font-weight:700;')
        self.set_colors(email_color, reader_color)

    def set_colors(self, email_color, reader_color):
        first = QColor(email_color); second = QColor(reader_color)
        email_color = first.name() if first.isValid() else "#F1F5F9"
        reader_color = second.name() if second.isValid() else "#629CFF"
        self.setText(f'<span style="color:{email_color}">Email</span><span style="color:{reader_color}">Reader</span>')
