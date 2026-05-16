"""Donation: VTB Paymo link and QR; Donatty planned when verified."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from buzz_mini.paths import assets_dir

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# URL сбора по умолчанию. Опционально BUZZMINI_DONATE_URL в окружении
# подставляет другую ссылку (удобно при смене платформы без правки кода).
_DEFAULT_DONATE_URL = (
    "https://vtb.paymo.ru/collect-money/?transaction=f77f0675-61b6-4914-bca1-97a2eff8c32d"
)


def _donate_qr_path() -> Path:
    return assets_dir() / "donate-qr.png"


class DonatePanel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        url = os.environ.get("BUZZMINI_DONATE_URL", _DEFAULT_DONATE_URL).strip() or _DEFAULT_DONATE_URL

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        body = QLabel()
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setText(
            "<p style='font-weight: 600; font-size: 13pt;'>Поддержать проект</p>"
            "<p style='margin-top: 8px;'>Если BuzzMini пригодился, можно перевести любую сумму "
            "через <b>ВТБ (Paymo)</b> — по кнопке ниже или по QR-коду. "
            "Профиль на Donatty пока на проверке; когда он заработает, добавим и его.</p>"
            "<p style='margin-top: 6px; color: palette(mid); font-size: 10pt;'>"
            f"<a href=\"{url}\">{url}</a></p>"
        )
        body.setOpenExternalLinks(True)
        layout.addWidget(body)

        qr_path = _donate_qr_path()
        if qr_path.is_file():
            pm = QPixmap(str(qr_path))
            if not pm.isNull():
                max_side = 220
                if max(pm.width(), pm.height()) > max_side:
                    pm = pm.scaled(
                        max_side,
                        max_side,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                qr = QLabel()
                qr.setPixmap(pm)
                qr.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                layout.addWidget(qr)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        donate_btn = QPushButton("Открыть страницу сбора (ВТБ)")
        donate_btn.setDefault(True)
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
