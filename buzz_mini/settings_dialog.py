"""Tray settings: push-to-talk chord + microphone (persistent, Buzz-style)."""

from __future__ import annotations

import os
import sys
from typing import Optional

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
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


class SettingsPanel(QWidget):
    """Settings form for a tab; click **Save settings** to persist."""

    settings_saved = pyqtSignal()

    def __init__(self, settings: DictateSettings, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
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

        self._close_tray = QCheckBox("Close button hides window to tray (Quit in tray menu exits)")
        self._close_tray.setChecked(settings.close_to_tray_on_window_close())
        layout.addWidget(self._close_tray)

        self._save_btn = QPushButton("Save settings")
        self._save_btn.clicked.connect(self._on_save)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save_row.addWidget(self._save_btn)
        layout.addLayout(save_row)

    def _on_save(self) -> None:
        self.apply()
        self.settings_saved.emit()

    def apply(self) -> None:
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
        self._settings.set_close_to_tray_on_window_close(self._close_tray.isChecked())


class SettingsDialog(QDialog):
    def __init__(self, settings: DictateSettings, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings — Buzz Mini")
        self._panel = SettingsPanel(settings, self)
        # Hide redundant save button — dialog uses OK
        self._panel._save_btn.hide()
        layout = QVBoxLayout(self)
        layout.addWidget(self._panel)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        self._panel.apply()
        self.accept()
