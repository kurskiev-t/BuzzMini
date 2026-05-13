"""Persist selected model and related prefs (Qt QSettings)."""

from __future__ import annotations

from PyQt6.QtCore import QSettings


class DictateSettings:
    ORG = "BuzzMini"
    APP = "BuzzMini"

    KEY_MODEL_ID = "selected_model_id"
    KEY_PTT_CHORD = "ptt_chord_id"
    KEY_INPUT_DEVICE = "input_device_index"

    PTT_CHORD_SPACE = "ctrl_r+space"
    PTT_CHORD_WIN = "ctrl_r+win"
    PTT_CHORD_CHOICES = (PTT_CHORD_SPACE, PTT_CHORD_WIN)

    def __init__(self) -> None:
        self._s = QSettings(self.ORG, self.APP)

    def selected_model_id(self) -> str:
        default = "large-v3-turbo"
        v = self._s.value(self.KEY_MODEL_ID, default)
        return str(v) if v else default

    def set_selected_model_id(self, model_id: str) -> None:
        self._s.setValue(self.KEY_MODEL_ID, model_id)

    def ptt_chord_id(self) -> str:
        v = self._s.value(self.KEY_PTT_CHORD, self.PTT_CHORD_SPACE)
        s = str(v).strip().lower().replace(" ", "") if v else self.PTT_CHORD_SPACE
        if s not in self.PTT_CHORD_CHOICES:
            return self.PTT_CHORD_SPACE
        return s

    def set_ptt_chord_id(self, chord_id: str) -> None:
        c = chord_id.strip().lower().replace(" ", "")
        if c not in self.PTT_CHORD_CHOICES:
            c = self.PTT_CHORD_SPACE
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
