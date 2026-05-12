"""Tray settings: push-to-talk chord + microphone (persistent, Buzz-style)."""

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

from buzz_dictate.audio_devices import input_devices_for_ui
from buzz_dictate.settings_store import DictateSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: DictateSettings, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings — Buzz Dictate")
        self._settings = settings

        layout = QVBoxLayout(self)

        env_ptt = os.environ.get("BUZZDICTATE_PTT_CHORD", "").strip()
        if env_ptt:
            layout.addWidget(
                QLabel(
                    "Push-to-talk is fixed by the environment variable\n"
                    "BUZZDICTATE_PTT_CHORD — remove it and restart to use the list below."
                )
            )

        env_dev = os.environ.get("BUZZDICTATE_AUDIO_DEVICE", "").strip()
        if env_dev:
            layout.addWidget(
                QLabel(
                    "Microphone is fixed by BUZZDICTATE_AUDIO_DEVICE\n"
                    "(integer index) — remove it to use the list below."
                )
            )

        form = QFormLayout()
        self._combo_ptt = QComboBox()
        self._combo_ptt.addItem("Right Ctrl + Space", DictateSettings.PTT_CHORD_SPACE)
        self._combo_ptt.addItem("Right Ctrl + Win", DictateSettings.PTT_CHORD_WIN)
        idx = self._combo_ptt.findData(settings.ptt_chord_id())
        self._combo_ptt.setCurrentIndex(max(0, idx))
        self._combo_ptt.setEnabled(not env_ptt)
        form.addRow("Push-to-talk:", self._combo_ptt)

        self._combo_mic = QComboBox()
        cur = settings.input_device_index()
        for dev_id, label in input_devices_for_ui():
            self._combo_mic.addItem(label, dev_id)
        for i in range(self._combo_mic.count()):
            if self._combo_mic.itemData(i) == cur:
                self._combo_mic.setCurrentIndex(i)
                break
        self._combo_mic.setEnabled(not env_dev)
        form.addRow("Microphone:", self._combo_mic)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        if self._combo_ptt.isEnabled():
            data = self._combo_ptt.currentData()
            if isinstance(data, str):
                self._settings.set_ptt_chord_id(data)
        if self._combo_mic.isEnabled():
            dev = self._combo_mic.currentData()
            self._settings.set_input_device_index(dev if dev is not None else None)
        super().accept()
