"""In-app log view: Qt handler + copy / clear."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LogEmitter(QObject):
    """Marshals log records from worker threads onto the GUI thread."""

    message = pyqtSignal(str)


class QtLogHandler(logging.Handler):
    def __init__(self, emitter: LogEmitter) -> None:
        super().__init__()
        self._emitter = emitter

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self._emitter.message.emit(msg)
        except Exception:
            self.handleError(record)


class LogPanel(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._emitter = LogEmitter()
        self._emitter.message.connect(self._append_line)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._log.setPlaceholderText("Log output from BuzzMini (INFO by default)…")

        hint = QLabel("Tip: set BUZZMINI_LOG_LEVEL=DEBUG for more detail.")
        hint.setStyleSheet("color: palette(mid);")

        row = QHBoxLayout()
        copy_btn = QPushButton("Copy all")
        copy_btn.clicked.connect(self._copy_all)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._log.clear)
        row.addWidget(copy_btn)
        row.addWidget(clear_btn)
        row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self._log, 1)
        layout.addLayout(row)

    def emitter(self) -> LogEmitter:
        return self._emitter

    def _append_line(self, line: str) -> None:
        self._log.appendPlainText(line)
        sb = self._log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _copy_all(self) -> None:
        t = self._log.toPlainText()
        if t:
            QGuiApplication.clipboard().setText(t)
