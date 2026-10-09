from __future__ import annotations
from PySide6.QtCore import Qt, QEvent, QObject, QRect
from shiboken6 import isValid
from PySide6.QtGui import QPainter, QPixmap, QColor, QPen
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QMenu
from app.utils.paths import resource_path
from app.version import APP_NAME, VERSION


class WindowButton(QPushButton):
    def __init__(self, kind, name, parent):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(46, 44)
        self.setAccessibleName(name); self.setToolTip(name)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton{min-width:0;min-height:0;padding:0;border:0;background:transparent;border-radius:0;} QPushButton:hover{background:#284762;} QPushButton:focus{border:1px solid #91BAFF;}" + ("QPushButton:hover{background:#C42B3D;}" if kind == "close" else ""))

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#F1F5F9"), 1.4))
        x, y = self.width() // 2, self.height() // 2
        if self.kind == "close":
            p.drawLine(x-5,y-5,x+5,y+5); p.drawLine(x+5,y-5,x-5,y+5)
        elif self.kind == "minimize": p.drawLine(x-5,y,x+5,y)
        elif self.window().isMaximized():
            p.drawRect(x-3,y-5,8,8); p.drawRect(x-5,y-3,8,8)
        else: p.drawRect(x-5,y-5,10,10)


class MountainTitleBar(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.owner = window
        self.background = QPixmap(str(resource_path("resources/titlebar-mountains.png")))
        self.setFixedHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12,0,0,0); layout.setSpacing(8)
        logo = QLabel(); logo.setPixmap(window.windowIcon().pixmap(24,24))
        title = QLabel(f"{APP_NAME}  v{VERSION}")
        title.setStyleSheet("background:transparent;color:#F1F5F9;font-size:14px;font-weight:600;")
        for label in (logo,title):
            label.setAttribute(Qt.WA_TransparentForMouseEvents); layout.addWidget(label)
        layout.addStretch()
        self.minimize = WindowButton("minimize","Minimize",self)
        self.maximize = WindowButton("maximize","Maximize",self)
        self.close_button = WindowButton("close","Close (Ctrl+W)",self)
        self.minimize.clicked.connect(window.showMinimized)
        self.maximize.clicked.connect(self.toggle_maximized)
        self.close_button.clicked.connect(window.close)
        for button in (self.minimize,self.maximize,self.close_button): layout.addWidget(button)
        window.installEventFilter(self)

    def paintEvent(self,event):
        p = QPainter(self); p.fillRect(self.rect(),QColor("#091725"))
        if not self.background.isNull():
            source = QRect(0,int(self.background.height()*.30),self.background.width(),int(self.background.height()*.45))
            p.drawPixmap(self.rect(),self.background,source)
        p.setPen(QColor("#28425C")); p.drawLine(0,self.height()-1,self.width(),self.height()-1)

    def toggle_maximized(self):
        self.owner.showNormal() if self.owner.isMaximized() else self.owner.showMaximized()

    def eventFilter(self,watched,event):
        if event.type() == QEvent.WindowStateChange:
            name = "Restore" if self.owner.isMaximized() else "Maximize"
            self.maximize.setAccessibleName(name); self.maximize.setToolTip(name); self.maximize.update()
        return False

    def mousePressEvent(self,event):
        if event.button() == Qt.LeftButton and self.owner.windowHandle():
            self.owner.windowHandle().startSystemMove(); event.accept()
        else: super().mousePressEvent(event)

    def mouseDoubleClickEvent(self,event):
        if event.button() == Qt.LeftButton: self.toggle_maximized(); event.accept()

    def contextMenuEvent(self,event):
        menu = QMenu(self)
        restore = menu.addAction("Restore",self.owner.showNormal); restore.setEnabled(self.owner.isMaximized())
        menu.addAction("Minimize",self.owner.showMinimized)
        maximize = menu.addAction("Maximize",self.owner.showMaximized); maximize.setEnabled(not self.owner.isMaximized())
        menu.addSeparator(); menu.addAction("Close (Ctrl+W)",self.owner.close)
        menu.exec(event.globalPos())


class WindowResizeFilter(QObject):
    """Native system resize from window edges, including over child widgets."""
    def __init__(self,window):
        super().__init__(window)
        self.owner = window
        self.hovered = None
        self.previous_cursor = None

    def edges_at(self,point):
        edges = Qt.Edges()
        if self.owner.isMaximized() or self.owner.isFullScreen(): return edges
        if point.x() < 5: edges |= Qt.LeftEdge
        elif point.x() >= self.owner.width()-5: edges |= Qt.RightEdge
        if point.y() < 5: edges |= Qt.TopEdge
        elif point.y() >= self.owner.height()-5: edges |= Qt.BottomEdge
        return edges

    def eventFilter(self,widget,event):
        if not isinstance(widget,QWidget) or widget.window() is not self.owner: return False
        if event.type() not in (QEvent.MouseMove,QEvent.MouseButtonPress,QEvent.Leave): return False
        if self.hovered and (widget is not self.hovered or event.type() == QEvent.Leave):
            if isValid(self.hovered): self.hovered.setCursor(self.previous_cursor)
            self.hovered = None
        if event.type() == QEvent.Leave: return False
        edges = self.edges_at(self.owner.mapFromGlobal(event.globalPosition().toPoint()))
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton and edges:
            handle = self.owner.windowHandle()
            return bool(handle and handle.startSystemResize(edges))
        if event.type() == QEvent.MouseMove:
            if edges:
                if self.hovered is None:
                    self.hovered = widget; self.previous_cursor = widget.cursor()
                if edges in (Qt.TopEdge|Qt.LeftEdge,Qt.BottomEdge|Qt.RightEdge): cursor = Qt.SizeFDiagCursor
                elif edges in (Qt.TopEdge|Qt.RightEdge,Qt.BottomEdge|Qt.LeftEdge): cursor = Qt.SizeBDiagCursor
                elif edges & (Qt.LeftEdge|Qt.RightEdge): cursor = Qt.SizeHorCursor
                else: cursor = Qt.SizeVerCursor
                widget.setCursor(cursor)
            elif self.hovered:
                if isValid(self.hovered): self.hovered.setCursor(self.previous_cursor)
                self.hovered = None
        return False
