"""Progress UI for model downloads (Faster Whisper has no byte-level progress in Buzz — indeterminate bar)."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QProgressDialog, QPushButton, QWidget


class ModelDownloadProgressDialog(QProgressDialog):
    """Matches Buzz `ModelDownloadProgressDialog` for FASTER_WHISPER: busy / indeterminate bar."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumWidth(360)
        self.setMinimumDuration(0)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setRange(0, 0)
        self.setLabelText("Downloading model…")
        self.setCancelButton(QPushButton("Cancel", self))
