"""Minimal always-on-top recording indicator."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class RecordingOverlay(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel(self)
        self._label.setStyleSheet(
            """
            QLabel {
                background-color: rgba(30, 30, 30, 220);
                color: #e0e0e0;
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 14px;
                font-family: Segoe UI, sans-serif;
            }
            """
        )
        self._label.setText("● Dictating…")

        layout.addWidget(self._label)
        self.adjustSize()
        self.hide()

    def show_listening(self) -> None:
        self._label.setText("● Dictating…")
        self.adjustSize()
        self._position_bottom_right()
        self.show()

    def show_transcribing(self) -> None:
        self._label.setText("… Transcribing")
        self.adjustSize()
        self._position_bottom_right()
        self.show()

    def hide_overlay(self) -> None:
        self.hide()

    def _position_bottom_right(self) -> None:
        screen = self.screen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        margin = 24
        self.adjustSize()
        self.move(
            geo.right() - self.width() - margin,
            geo.bottom() - self.height() - margin,
        )
