"""Progress UI for HF model snapshots (busy bar + textual status below)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class ModelDownloadProgressDialog(QDialog):
    """Busy (indeterminate) bar with a secondary line for progress text or errors."""

    canceled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Buzz Mini")
        self.setModal(True)
        self.setMinimumWidth(400)

        self._cancel_emitted = False
        self._error_mode = False

        self._head = QLabel("Downloading model…")
        self._head.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)
        self._bar.setTextVisible(False)

        self._detail = QLabel("Preparing…")
        self._detail.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._detail.setWordWrap(True)
        self._detail.setMinimumHeight(44)
        self._apply_detail_palette()

        self._action_btn = QPushButton("Cancel")
        self._action_btn.clicked.connect(self._on_action_clicked)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self._action_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._head)
        layout.addWidget(self._bar)
        layout.addWidget(self._detail)
        layout.addLayout(btn_row)

    def _apply_detail_palette(self) -> None:
        c = self.palette().color(QPalette.ColorRole.PlaceholderText)
        if not c.isValid():
            c = self.palette().color(QPalette.ColorRole.ToolTipText)
        self._detail.setStyleSheet(f"color:{c.name()};")

    def _emit_cancel_once(self) -> None:
        if self._cancel_emitted or self._error_mode:
            return
        self._cancel_emitted = True
        self.canceled.emit()

    def _on_action_clicked(self) -> None:
        if self._error_mode:
            self.accept()
        else:
            self.reject()

    def reject(self) -> None:
        self._emit_cancel_once()
        super().reject()

    def closeEvent(self, event):  # type: ignore[override]
        if self._error_mode:
            self.done(QDialog.DialogCode.Accepted)
            event.accept()
            return
        self._emit_cancel_once()
        super().closeEvent(event)

    def disconnect_cancel(self, slot: Callable[..., object]) -> None:
        """Detach cancel handler before programmatic close (success / aborted)."""
        try:
            self.canceled.disconnect(slot)
        except TypeError:
            pass

    def set_detail_text(self, text: str) -> None:
        """Update the line under the progress bar (during download)."""
        if self._error_mode:
            return
        self._detail.setText(text)

    def show_error(self, message: str) -> None:
        """Switch to failure layout; keep dialog open until the user dismisses it."""
        self._error_mode = True
        self._head.setText("Download failed")
        self._bar.setVisible(False)
        err = QColor("#e57373")
        self._detail.setText(message)
        self._detail.setStyleSheet(f"color:{err.name()};")
        self._action_btn.setText("Close")
        logger.error("Model download failed: %s", message)
