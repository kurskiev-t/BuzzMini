from __future__ import annotations

from typing import Protocol

import numpy as np


class TranscriptionBackend(Protocol):
    model_id: str

    def set_model_id(self, model_id: str) -> None: ...

    def load(self) -> None: ...

    def unload(self) -> None: ...

    def transcribe(self, audio_float32: np.ndarray, sample_rate: int, language: str | None) -> str: ...
