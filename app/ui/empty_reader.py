from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPixmap, QPen, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from app.utils.paths import resource_path


class Envelope(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 44)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QColor('#7795B3'), 1.5))
        painter.drawRoundedRect(QRectF(4, 6, 44, 32), 3, 3)
        painter.drawLine(5, 8, 26, 24)
        painter.drawLine(26, 24, 47, 8)


class EmptyReader(QWidget):
    """Native placeholder avoids the WebEngine white page during startup."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.background = QPixmap(str(resource_path('resources/reader-empty-mountains.png')))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addStretch(3)
        layout.addWidget(Envelope(), 0, Qt.AlignHCenter)
        title = QLabel('Select an email')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('background:transparent;color:#D5E4F2;font-size:22px;font-weight:500;')
        layout.addWidget(title)
        subtitle = QLabel('Choose a message from the list to read it.')
        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet('background:transparent;color:#90ABC4;font-size:13px;')
        layout.addWidget(subtitle)
        layout.addStretch(4)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#0B121B'))
        if not self.background.isNull():
            # Fit horizontally so the mountain range remains visible in narrow panes.
            target_height = self.width() * self.background.height() / self.background.width()
            painter.drawPixmap(QRectF(0, self.height() - target_height, self.width(), target_height),
                               self.background, QRectF(self.background.rect()))
