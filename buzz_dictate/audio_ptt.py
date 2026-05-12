"""Push-to-talk capture via sounddevice (float32 mono), Buzz-style sample-rate pick."""

from __future__ import annotations

import logging
import threading
from typing import Optional

import numpy as np
import sounddevice as sd
from sounddevice import PortAudioError

logger = logging.getLogger(__name__)


def resolve_sample_rate(device_id: Optional[int]) -> int:
    target = 16000
    try:
        sd.check_input_settings(device=device_id, samplerate=target)
        return target
    except PortAudioError:
        info = sd.query_devices(device=device_id)
        if isinstance(info, dict):
            return int(info.get("default_samplerate", target))
        return target


class PTTCapture:
    """Accumulates microphone samples while the push-to-talk stream is active."""

    def __init__(self, device_index: Optional[int] = None) -> None:
        self.device_index = device_index
        self.sample_rate = resolve_sample_rate(device_index)
        self._buf = np.array([], dtype=np.float32)
        self._lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None

    def start(self) -> None:
        self.stop()
        self._buf = np.array([], dtype=np.float32)

        def callback(indata: np.ndarray, frames: int, _time, status) -> None:
            if status:
                logger.debug("sounddevice status: %s", status)
            chunk = indata.ravel().astype(np.float32, copy=False)
            with self._lock:
                self._buf = np.append(self._buf, chunk)

        self._stream = sd.InputStream(
            device=self.device_index,
            samplerate=self.sample_rate,
            dtype="float32",
            channels=1,
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> tuple[np.ndarray, int]:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                logger.exception("Error closing InputStream")
            self._stream = None
        with self._lock:
            samples = self._buf
            self._buf = np.array([], dtype=np.float32)
        return samples, self.sample_rate
