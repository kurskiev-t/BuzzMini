"""Donation: CloudTips payment page."""

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# URL по умолчанию. Опционально BUZZMINI_DONATE_URL в окружении
# подставляет другую ссылку (удобно при смене платформы без правки кода).
_DEFAULT_DONATE_URL = "https://pay.cloudtips.ru/p/3fbf7934"


class DonatePanel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        url = os.environ.get("BUZZMINI_DONATE_URL", _DEFAULT_DONATE_URL).strip() or _DEFAULT_DONATE_URL

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("Поддержать проект")
        title.setWordWrap(True)
        title.setStyleSheet("font-weight: 600; font-size: 15pt;")
        layout.addWidget(title)

        body = QLabel()
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setOpenExternalLinks(True)
        body.setText(
            "<p>Если BuzzMini пригодился, можно поддержать автора "
            "(<b>Тимур К.</b>) любой суммой через <b>CloudTips</b> — "
            "карты российских банков, СБП и другие способы на странице оплаты.</p>"
            f"<p><a href=\"{url}\">{url}</a></p>"
        )
        layout.addWidget(body)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        donate_btn = QPushButton("Открыть страницу доната")
        donate_btn.setDefault(True)
        donate_btn.setMinimumWidth(220)
        donate_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        btn_row.addWidget(donate_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        layout.addStretch(1)


class DonateDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О донате")
        self.setModal(True)
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        layout.addWidget(DonatePanel(self))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
