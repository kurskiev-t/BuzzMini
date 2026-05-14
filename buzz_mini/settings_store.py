"""Persist selected model and related prefs (Qt QSettings)."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QSettings


class DictateSettings:
    ORG = "BuzzMini"
    APP = "BuzzMini"

    KEY_MODEL_ID = "selected_model_id"
    KEY_PTT_CHORD = "ptt_chord_id"
    KEY_INPUT_DEVICE = "input_device_index"
    KEY_CLOSE_TO_TRAY = "close_to_tray_on_window_close"

    # Canonical chord ids: left/right Ctrl + Space or Win/Cmd/Super (pynput Key.cmd).
    DEFAULT_PTT_CHORD = "ctrl_l+space"
    PTT_CHORD_CTRL_L_SPACE = "ctrl_l+space"
    PTT_CHORD_CTRL_L_WIN = "ctrl_l+win"
    PTT_CHORD_CTRL_R_SPACE = "ctrl_r+space"
    PTT_CHORD_CTRL_R_WIN = "ctrl_r+win"
    PTT_CHORD_CHOICES = (
        PTT_CHORD_CTRL_L_SPACE,
        PTT_CHORD_CTRL_L_WIN,
        PTT_CHORD_CTRL_R_SPACE,
        PTT_CHORD_CTRL_R_WIN,
    )

    def __init__(self) -> None:
        self._s = QSettings(self.ORG, self.APP)

    def selected_model_id(self) -> str:
        default = "large-v3-turbo"
        v = self._s.value(self.KEY_MODEL_ID, default)
        return str(v) if v else default

    def set_selected_model_id(self, model_id: str) -> None:
        self._s.setValue(self.KEY_MODEL_ID, model_id)

    def ptt_chord_id(self) -> str:
        v = self._s.value(self.KEY_PTT_CHORD, self.DEFAULT_PTT_CHORD)
        s = str(v).strip().lower().replace(" ", "") if v else self.DEFAULT_PTT_CHORD
        # Migrate older / informal chord strings to canonical ids.
        legacy = {
            "ctrl_r+space": self.PTT_CHORD_CTRL_R_SPACE,
            "ctrl_r+win": self.PTT_CHORD_CTRL_R_WIN,
            "ctrl+space": self.PTT_CHORD_CTRL_L_SPACE,
            "control+space": self.PTT_CHORD_CTRL_L_SPACE,
            "ctrl+win": self.PTT_CHORD_CTRL_L_WIN,
            "control+win": self.PTT_CHORD_CTRL_L_WIN,
        }
        s = legacy.get(s, s)
        if s not in self.PTT_CHORD_CHOICES:
            return self.DEFAULT_PTT_CHORD
        return s

    def set_ptt_chord_id(self, chord_id: str) -> None:
        c = chord_id.strip().lower().replace(" ", "")
        if c not in self.PTT_CHORD_CHOICES:
            c = self.DEFAULT_PTT_CHORD
        self._s.setValue(self.KEY_PTT_CHORD, c)

    def input_device_index(self) -> Optional[int]:
        """None = PortAudio default input."""
        v = self._s.value(self.KEY_INPUT_DEVICE, -1)
        try:
            i = int(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        return None if i < 0 else i

    def set_input_device_index(self, index: Optional[int]) -> None:
        self._s.setValue(self.KEY_INPUT_DEVICE, -1 if index is None else int(index))

    def close_to_tray_on_window_close(self) -> bool:
        """When True, closing the main window hides to tray instead of exiting."""
        v = self._s.value(self.KEY_CLOSE_TO_TRAY, True)
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower() if v is not None else "true"
        return s not in ("0", "false", "no", "off")

    def set_close_to_tray_on_window_close(self, value: bool) -> None:
        self._s.setValue(self.KEY_CLOSE_TO_TRAY, bool(value))
