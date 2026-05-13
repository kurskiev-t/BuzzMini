"""Tray settings: push-to-talk chord + microphone (persistent, Buzz-style)."""

from __future__ import annotations

import os
import sys
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

from buzz_mini.audio_devices import input_devices_for_ui
from buzz_mini.settings_store import DictateSettings


def _split_chord(chord_id: str) -> tuple[str, str]:
    a, _, b = chord_id.partition("+")
    return a.strip(), b.strip()


def _join_chord(mod: str, partner: str) -> str:
    return f"{mod.strip().lower()}+{partner.strip().lower()}"


class SettingsDialog(QDialog):
    def __init__(self, settings: DictateSettings, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings — Buzz Mini")
        self._settings = settings

        layout = QVBoxLayout(self)

        env_ptt = os.environ.get("BUZZMINI_PTT_CHORD", "").strip()
        if env_ptt:
            layout.addWidget(
                QLabel(
                    "Push-to-talk is fixed by the environment variable\n"
                    "BUZZMINI_PTT_CHORD — remove it and restart to use the lists below."
                )
            )

        env_dev = os.environ.get("BUZZMINI_AUDIO_DEVICE", "").strip()
        if env_dev:
            layout.addWidget(
                QLabel(
                    "Microphone is fixed by BUZZMINI_AUDIO_DEVICE\n"
                    "(integer index) — remove it to use the list below."
                )
            )

        form = QFormLayout()

        self._combo_mod = QComboBox()
        self._combo_mod.addItem("Left Ctrl", "ctrl_l")
        self._combo_mod.addItem("Right Ctrl", "ctrl_r")
        self._combo_partner = QComboBox()
        self._combo_partner.addItem("Space", "space")
        win_label = "Win" if os.name == "nt" else ("Cmd" if sys.platform == "darwin" else "Super")
        self._combo_partner.addItem(win_label, "win")

        cur = settings.ptt_chord_id()
        mod, partner = _split_chord(cur)
        for i in range(self._combo_mod.count()):
            if self._combo_mod.itemData(i) == mod:
                self._combo_mod.setCurrentIndex(i)
                break
        for i in range(self._combo_partner.count()):
            if self._combo_partner.itemData(i) == partner:
                self._combo_partner.setCurrentIndex(i)
                break

        self._combo_mod.setEnabled(not env_ptt)
        self._combo_partner.setEnabled(not env_ptt)
        form.addRow("PTT — Ctrl key:", self._combo_mod)
        form.addRow("PTT — second key:", self._combo_partner)

        self._combo_mic = QComboBox()
        cur_dev = settings.input_device_index()
        for dev_id, label in input_devices_for_ui():
            self._combo_mic.addItem(label, dev_id)
        for i in range(self._combo_mic.count()):
            if self._combo_mic.itemData(i) == cur_dev:
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
        if self._combo_mod.isEnabled() and self._combo_partner.isEnabled():
            mod = self._combo_mod.currentData()
            partner = self._combo_partner.currentData()
            if isinstance(mod, str) and isinstance(partner, str):
                joined = _join_chord(mod, partner)
                if joined in DictateSettings.PTT_CHORD_CHOICES:
                    self._settings.set_ptt_chord_id(joined)
        if self._combo_mic.isEnabled():
            dev = self._combo_mic.currentData()
            self._settings.set_input_device_index(dev if dev is not None else None)
        super().accept()
