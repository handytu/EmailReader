from __future__ import annotations
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QCheckBox,
    QPushButton, QFrame, QFormLayout, QDialogButtonBox, QColorDialog
)
from PySide6.QtGui import QColor
from app.services.settings_service import AppSettings
from app.ui.brand_label import BrandLabel

class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.settings = settings

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(16)

        title = QLabel("Settings")
        title.setStyleSheet("font-size:20px;font-weight:600;")
        root.addWidget(title)
        subtitle = QLabel("Customize how EmailReader looks and behaves.")
        subtitle.setObjectName("muted")
        root.addWidget(subtitle)

        card = QFrame()
        card.setStyleSheet("QFrame{background:#101822;border:1px solid #1F2C3C;border-radius:10px;}")
        form = QFormLayout(card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)

        self.messages_per_load = QComboBox()
        self.messages_per_load.addItems(["25", "50", "100"])
        self.messages_per_load.setCurrentText(str(settings.messages_per_load))
        form.addRow("Messages per load", self.messages_per_load)

        self.density = QComboBox()
        self.density.addItem("Comfortable", "comfortable")
        self.density.addItem("Compact", "compact")
        idx = self.density.findData(settings.density)
        self.density.setCurrentIndex(max(0, idx))
        form.addRow("Message density", self.density)
        self.brand_email_color = settings.brand_email_color
        self.brand_reader_color = settings.brand_reader_color
        self.brand_preview = BrandLabel(self.brand_email_color,self.brand_reader_color)
        form.addRow("App name preview",self.brand_preview)
        self.email_color_button = QPushButton()
        self.reader_color_button = QPushButton()
        self.email_color_button.clicked.connect(lambda: self._choose_brand_color("email"))
        self.reader_color_button.clicked.connect(lambda: self._choose_brand_color("reader"))
        form.addRow('Color of "Email"',self.email_color_button)
        form.addRow('Color of "Reader"',self.reader_color_button)
        self._update_brand_preview()

        self.block_remote_images = QCheckBox("Block remote images by default")
        self.block_remote_images.setChecked(settings.block_remote_images)
        form.addRow("Privacy", self.block_remote_images)

        self.confirm_delete = QCheckBox("Ask before deleting email")
        self.confirm_delete.setChecked(settings.confirm_delete)
        form.addRow("Delete", self.confirm_delete)

        self.open_last = QCheckBox("Open last selected account at startup")
        self.open_last.setChecked(settings.open_last_selected_account)
        form.addRow("Startup", self.open_last)
        self.auto_refresh = QCheckBox("Refresh the current account every 10 seconds")
        self.auto_refresh.setChecked(settings.auto_refresh)
        form.addRow("Sync", self.auto_refresh)

        root.addWidget(card)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        root.addWidget(buttons)

    def values(self) -> AppSettings:
        return AppSettings(
            messages_per_load=int(self.messages_per_load.currentText()),
            density=self.density.currentData(),
            block_remote_images=self.block_remote_images.isChecked(),
            confirm_delete=self.confirm_delete.isChecked(),
            open_last_selected_account=self.open_last.isChecked(),
            last_selected_account=self.settings.last_selected_account,
            auto_refresh=self.auto_refresh.isChecked(),
            brand_email_color=self.brand_email_color,
            brand_reader_color=self.brand_reader_color,
        )

    def _choose_brand_color(self,part):
        attr = f"brand_{part}_color"
        color = QColorDialog.getColor(QColor(getattr(self,attr)),self,f'Color of {part.title()}')
        if color.isValid():
            setattr(self,attr,color.name()); self._update_brand_preview()

    def _update_brand_preview(self):
        self.brand_preview.set_colors(self.brand_email_color,self.brand_reader_color)
        for button,color in ((self.email_color_button,self.brand_email_color),(self.reader_color_button,self.brand_reader_color)):
            button.setText(f"Choose color — {color.upper()}")
