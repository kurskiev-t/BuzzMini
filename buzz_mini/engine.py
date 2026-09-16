"""
Transcription facade: picks backend from BUZZMINI_BACKEND (cuda | vulkan | cpu | auto).
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from buzz_mini.backends.faster_whisper_backend import (
    FasterWhisperBackend,
    cuda_unavailable_reason,
)
from buzz_mini.backends.select import resolve_backend_name
from buzz_mini.backends.whispercpp_backend import (
    WhisperCppBackend,
    resolve_ggml_model,
    resolve_whisper_cli,
)
from buzz_mini.whisper_common import WHISPER_SR, resample_linear, resolve_download_root

# Back-compat aliases
_resolve_download_root = resolve_download_root

logger = logging.getLogger(__name__)


def transcription_device_summary() -> tuple[str, str | None]:
    """Short UI label and optional warning (Settings, tray). Honors BUZZMINI_BACKEND."""
    backend = resolve_backend_name()
    if backend == "vulkan":
        try:
            cli = resolve_whisper_cli()
            ggml = resolve_ggml_model()
            return f"GPU (Vulkan / whisper.cpp): {ggml.name}", None
        except FileNotFoundError as e:
            return "Vulkan (not configured)", str(e)
    if backend == "cpu":
        return "CPU (faster-whisper)", None

    try:
        import torch

        cuda_ok = torch.cuda.is_available()
        cuda_ver = getattr(torch.version, "cuda", None)
    except Exception:
        cuda_ok = False
        cuda_ver = None

    if cuda_ok:
        try:
            gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            gpu_name = "CUDA"
        return f"GPU (CUDA): {gpu_name}", None
    return "CPU (faster-whisper)", cuda_unavailable_reason(cuda_ok=False, cuda_ver=cuda_ver)


def _create_backend(name: str, model_id: str):
    if name == "vulkan":
        return WhisperCppBackend(model_id)
    if name == "cpu":
        return FasterWhisperBackend(model_id, force_cpu=True)
    return FasterWhisperBackend(model_id, force_cpu=False)


class WhisperEngine:
    """Delegates to faster-whisper (cuda/cpu) or whisper.cpp (vulkan)."""

    def __init__(self, model_size_or_path: Optional[str] = None) -> None:
        self.model_size_or_path = model_size_or_path or os.environ.get(
            "BUZZMINI_MODEL", "large-v3-turbo"
        )
        self._backend_name = resolve_backend_name()
        self._impl = _create_backend(self._backend_name, self.model_size_or_path)
        logger.info("Transcription backend=%s model=%s", self._backend_name, self.model_size_or_path)

    def set_model_id(self, model_id: str) -> None:
        self.model_size_or_path = model_id
        self._impl.set_model_id(model_id)

    def unload(self) -> None:
        self._impl.unload()

    def load(self) -> None:
        self._backend_name = resolve_backend_name()
        self._impl = _create_backend(self._backend_name, self.model_size_or_path)
        logger.info("Loading backend=%s", self._backend_name)
        self._impl.load()

    def transcribe(self, audio_float32, sample_rate: int, language: str | None) -> str:
        return self._impl.transcribe(audio_float32, sample_rate, language)

    @property
    def backend_name(self) -> str:
        return self._backend_name
