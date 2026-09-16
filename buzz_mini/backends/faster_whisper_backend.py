from __future__ import annotations

import logging
import os
import platform
import sys
from typing import Optional

import numpy as np

from buzz_mini import cuda_setup  # noqa: F401
from buzz_mini.backends.gpu_detect import (
    has_amd_adapter,
    has_nvidia_adapter,
    win32_video_adapter_names,
)
from buzz_mini.whisper_common import WHISPER_SR, log_cuda_unavailable, resample_linear, resolve_download_root

import faster_whisper
import torch

logger = logging.getLogger(__name__)


def _cuda_major(version: str | None) -> int | None:
    if not version or not str(version).strip():
        return None
    base = str(version).split("+", 1)[0].strip()
    head = base.split(".", 1)[0].strip()
    if not head.isdigit():
        return None
    return int(head)


def _cuda_build_available(cuda_ver: object) -> bool:
    if not isinstance(cuda_ver, str):
        return False
    return bool(cuda_ver.strip())


def cuda_unavailable_reason(*, cuda_ok: bool, cuda_ver: object) -> str | None:
    if cuda_ok:
        return None
    if not _cuda_build_available(cuda_ver):
        if sys.platform == "win32":
            return (
                "This install uses CPU-only PyTorch (no CUDA). "
                "Developer builds need CUDA torch (uv sync or PyTorch cu126 index); "
                "end users need the Buzz Mini NVIDIA (cuda) release build."
            )
        return "This install uses CPU-only PyTorch (no CUDA)."

    names = win32_video_adapter_names()
    if has_nvidia_adapter(names):
        return (
            "NVIDIA GPU detected but CUDA is not available — update the NVIDIA driver "
            "or reinstall Buzz Mini from the cuda release build."
        )
    if has_amd_adapter(names):
        return (
            "AMD GPU detected — use the Buzz Mini amd release build (Vulkan) or set "
            "BUZZMINI_BACKEND=vulkan with whisper.cpp; this cuda build runs on CPU only. "
            "For speed, pick a smaller model (e.g. Small or Base)."
        )
    return (
        "No NVIDIA CUDA device is available; transcription runs on CPU. "
        "GPU acceleration on NVIDIA requires the cuda release build."
    )


class FasterWhisperBackend:
    """faster-whisper + CTranslate2 (CUDA or CPU)."""

    def __init__(self, model_size_or_path: Optional[str] = None, *, force_cpu: bool = False) -> None:
        self.model_id = model_size_or_path or os.environ.get("BUZZMINI_MODEL", "large-v3-turbo")
        self._force_cpu = force_cpu
        self._model: faster_whisper.WhisperModel | None = None
        self._device: str = "cpu"

    def set_model_id(self, model_id: str) -> None:
        self.model_id = model_id

    @property
    def device(self) -> str:
        return self._device

    def unload(self) -> None:
        self._model = None
        import gc

        gc.collect()
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def load(self) -> None:
        model_root_dir = resolve_download_root()
        os.makedirs(model_root_dir, exist_ok=True)
        logger.info("faster-whisper download_root=%s", model_root_dir)

        force_cpu = self._force_cpu or os.environ.get(
            "BUZZMINI_FORCE_CPU", os.environ.get("BUZZ_FORCE_CPU", "false")
        ) != "false"
        cuda_ok = torch.cuda.is_available()
        cuda_ver = getattr(torch.version, "cuda", None)
        cuda_major = _cuda_major(cuda_ver if isinstance(cuda_ver, str) else None)
        too_old_cuda = cuda_ok and cuda_major is not None and cuda_major < 12

        device_env = os.environ.get("BUZZMINI_DEVICE", "").strip().lower()

        if device_env == "cpu":
            device = "cpu"
        elif device_env == "cuda":
            device = "cuda" if cuda_ok else "cpu"
        elif device_env == "auto":
            device = "auto"
        elif too_old_cuda:
            device = "cpu"
            logger.info(
                "CUDA %s (major %s) < 12 — using CPU for CTranslate2 compatibility",
                cuda_ver,
                cuda_major,
            )
        elif cuda_ok and not force_cpu:
            device = "cuda"
        else:
            device = "cpu"

        if force_cpu:
            device = "cpu"

        if device == "cuda" and not cuda_ok:
            logger.warning("BUZZMINI_DEVICE=cuda but torch.cuda.is_available() is False; using CPU")
            device = "cpu"

        if device == "auto":
            device = "cuda" if (cuda_ok and not force_cpu and not too_old_cuda) else "cpu"

        self._device = device

        logger.info(
            "interpreter=%s torch.cuda=%s torch.version.cuda=%r cuda_major=%s -> faster-whisper device=%s",
            sys.executable,
            cuda_ok,
            cuda_ver,
            cuda_major,
            device,
        )
        if not cuda_ok and not force_cpu and device == "cpu":
            log_cuda_unavailable(cuda_ver)

        reduce_gpu_memory = os.environ.get("BUZZ_REDUCE_GPU_MEMORY", "false") != "false" or os.environ.get(
            "BUZZMINI_REDUCE_VRAM", ""
        ).lower() in ("1", "true", "yes")
        compute_type = "default"
        if reduce_gpu_memory:
            compute_type = "int8" if device == "cpu" else "int8_float16"
            logger.debug("Using %s for reduced memory", compute_type)

        logger.info(
            "Loading faster-whisper model=%s device=%s compute_type=%s",
            self.model_id,
            device,
            compute_type,
        )
        self._model = faster_whisper.WhisperModel(
            model_size_or_path=self.model_id,
            download_root=model_root_dir,
            device=device,
            compute_type=compute_type,
            cpu_threads=max(1, (os.cpu_count() or 8) // 2),
        )

    def transcribe(self, audio_float32: np.ndarray, sample_rate: int, language: str | None) -> str:
        if self._model is None:
            raise RuntimeError("FasterWhisperBackend.load() was not called")

        mono = audio_float32.astype(np.float32, copy=False)
        if mono.ndim > 1:
            mono = mono.mean(axis=1)
        audio_in = resample_linear(mono, sample_rate, WHISPER_SR)

        lang = language if language else None
        temperature = 0 if platform.system() == "Windows" else 0.2

        segments, _info = self._model.transcribe(
            audio=audio_in,
            language=lang,
            task="transcribe",
            temperature=temperature,
            initial_prompt=os.environ.get("BUZZMINI_INITIAL_PROMPT", "") or "",
            word_timestamps=False,
            without_timestamps=True,
            no_speech_threshold=0.4,
        )
        parts = [s.text.strip() for s in segments]
        return " ".join(parts).strip()
