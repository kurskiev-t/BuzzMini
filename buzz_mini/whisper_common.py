"""Shared helpers for all Whisper backends."""

from __future__ import annotations

import logging
import os
import sys

import numpy as np
from platformdirs import user_cache_dir

from buzz_mini.backends.gpu_detect import (
    has_amd_adapter,
    has_nvidia_adapter,
    win32_video_adapter_names,
)

logger = logging.getLogger(__name__)

WHISPER_SR = 16000


def resolve_download_root() -> str:
    if os.environ.get("BUZZMINI_MODEL_ROOT"):
        return os.environ["BUZZMINI_MODEL_ROOT"]
    if os.environ.get("BUZZ_MODEL_ROOT"):
        return os.environ["BUZZ_MODEL_ROOT"]
    here = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(here)
    if os.path.isfile(os.path.join(parent, "pyproject.toml")):
        return os.path.join(parent, "models")
    buzz_models = os.path.join(user_cache_dir("Buzz"), "models")
    if os.path.isdir(buzz_models):
        return buzz_models
    return os.path.join(user_cache_dir("BuzzMini"), "models")


def resample_linear(samples: np.ndarray, orig_sr: int, target_sr: int = WHISPER_SR) -> np.ndarray:
    if orig_sr == target_sr:
        return samples.astype(np.float32, copy=False)
    duration = len(samples) / orig_sr
    n_out = max(1, int(duration * target_sr))
    x_old = np.linspace(0.0, duration, num=len(samples), endpoint=False)
    x_new = np.linspace(0.0, duration, num=n_out, endpoint=False)
    out = np.interp(x_new, x_old, samples.astype(np.float64)).astype(np.float32)
    return out


def _cuda_build_available(cuda_ver: object) -> bool:
    if not isinstance(cuda_ver, str):
        return False
    return bool(cuda_ver.strip())


def log_cuda_unavailable(cuda_ver: object) -> None:
    if _cuda_build_available(cuda_ver):
        from buzz_mini.backends.faster_whisper_backend import cuda_unavailable_reason

        detail = cuda_unavailable_reason(cuda_ok=False, cuda_ver=cuda_ver)
        logger.warning("CUDA is off — %s", detail)
        return
    if sys.platform == "win32":
        logger.warning(
            "CUDA is off — CPU-only PyTorch in %s. On Windows, plain `pip install -e .` "
            "often installs CPU torch from PyPI; use `uv sync` or reinstall torch from the "
            "PyTorch CUDA index (README: pip install torch --index-url "
            "https://download.pytorch.org/whl/cu126).",
            sys.executable,
        )
    else:
        logger.warning(
            "CUDA is off — CPU-only PyTorch in %s (usually wrong venv or CPU wheel).",
            sys.executable,
        )
