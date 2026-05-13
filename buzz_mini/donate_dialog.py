"""Modal dialog: donation info + link to Donatty."""

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtCore import QUrl, Qt
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

# Replace with your profile URL when ready (or set BUZZMINI_DONATE_URL).
_DEFAULT_DONATTY = "https://donatty.com"


class DonateDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("О донате")
        self.setModal(True)
        self.setMinimumWidth(440)

        url = os.environ.get("BUZZMINI_DONATE_URL", _DEFAULT_DONATTY).strip() or _DEFAULT_DONATTY

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        body = QLabel()
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setText(
            "<p style='font-weight: 600; font-size: 13pt;'>Поддержать проект ❤️</p>"
            "<p style='margin-top: 8px;'>Спасибо, что используете программу для голосового ввода! "
            "Проект развивается исключительно на энтузиазме автора. Ваши донаты помогают мне "
            "адаптировать новые ИИ-модели и развивать проект. Принимаются карты РФ, СБП и "
            "зарубежные карты.</p>"
        )
        layout.addWidget(body)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        donate_btn = QPushButton("Поддержать на Donatty")
        donate_btn.setDefault(True)
        donate_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        btn_row.addWidget(donate_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
