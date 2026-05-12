"""Minimal tray settings: push-to-talk chord (Handy-style global hotkeys stay in app + pynput)."""

from __future__ import annotations

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from buzz_dictate.settings_store import DictateSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: DictateSettings, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings — Buzz Dictate")
        self._settings = settings

        layout = QVBoxLayout(self)

        env = os.environ.get("BUZZDICTATE_PTT_CHORD", "").strip()
        if env:
            layout.addWidget(
                QLabel(
                    "Push-to-talk is fixed by the environment variable\n"
                    "BUZZDICTATE_PTT_CHORD — remove it and restart to use the list below."
                )
            )

        form = QFormLayout()
        self._combo = QComboBox()
        self._combo.addItem("Right Ctrl + Space", DictateSettings.PTT_CHORD_SPACE)
        self._combo.addItem("Right Ctrl + Win", DictateSettings.PTT_CHORD_WIN)
        idx = self._combo.findData(settings.ptt_chord_id())
        self._combo.setCurrentIndex(max(0, idx))
        self._combo.setEnabled(not env)
        form.addRow("Push-to-talk:", self._combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        if self._combo.isEnabled():
            data = self._combo.currentData()
            if isinstance(data, str):
                self._settings.set_ptt_chord_id(data)
        super().accept()
