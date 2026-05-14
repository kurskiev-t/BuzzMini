"""
Local faster-whisper engine: load once, transcribe complete utterances.
Device / compute / model-root logic aligned with Buzz `RecordingTranscriber` + `whisper_file_transcriber`.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from typing import Optional

import numpy as np
from platformdirs import user_cache_dir

from buzz_mini import cuda_setup  # noqa: F401

import faster_whisper
import torch

logger = logging.getLogger(__name__)

WHISPER_SR = 16000


def _cuda_major(version: str | None) -> int | None:
    """Parse major from torch.version.cuda (e.g. '12.6', '12.6+cu126'). None if unknown."""
    if not version or not str(version).strip():
        return None
    base = str(version).split("+", 1)[0].strip()
    head = base.split(".", 1)[0].strip()
    if not head.isdigit():
        return None
    return int(head)


def _resolve_download_root() -> str:
    """Weights + HF snapshot_download cache directory.

    Priority: BUZZMINI_MODEL_ROOT, BUZZ_MODEL_ROOT, then ``<repo>/models`` when running
    from a source tree (``pyproject.toml`` next to the ``buzz_mini`` package), else Buzz
    legacy cache if present, else ``user_cache_dir('BuzzMini')/models``.
    """
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


class WhisperEngine:
    """Holds a single `faster_whisper.WhisperModel` instance."""

    def __init__(self, model_size_or_path: Optional[str] = None) -> None:
        self.model_size_or_path = model_size_or_path or os.environ.get(
            "BUZZMINI_MODEL", "large-v3-turbo"
        )
        self._model: faster_whisper.WhisperModel | None = None

    def set_model_id(self, model_id: str) -> None:
        self.model_size_or_path = model_id

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
        model_root_dir = _resolve_download_root()
        os.makedirs(model_root_dir, exist_ok=True)
        logger.info("faster-whisper download_root=%s", model_root_dir)

        force_cpu = os.environ.get("BUZZMINI_FORCE_CPU", os.environ.get("BUZZ_FORCE_CPU", "false"))
        cuda_ok = torch.cuda.is_available()
        cuda_ver = getattr(torch.version, "cuda", None)
        cuda_major = _cuda_major(cuda_ver if isinstance(cuda_ver, str) else None)

        # Never use string compare on version: e.g. "" < "12" is True in Python and would
        # incorrectly force CPU while CUDA works (some torch builds report empty cuda string).
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
        elif cuda_ok:
            # Default when unset: explicit "cuda" (not "auto") — more reliable with CTranslate2 on Windows.
            device = "cuda"
        else:
            device = "cpu"

        if force_cpu != "false":
            device = "cpu"

        if device == "cuda" and not cuda_ok:
            logger.warning("BUZZMINI_DEVICE=cuda but torch.cuda.is_available() is False; using CPU")
            device = "cpu"

        if device == "auto":
            device = "cuda" if (cuda_ok and force_cpu == "false" and not too_old_cuda) else "cpu"

        logger.info(
            "interpreter=%s torch.cuda=%s torch.version.cuda=%r cuda_major=%s -> faster-whisper device=%s",
            sys.executable,
            cuda_ok,
            cuda_ver,
            cuda_major,
            device,
        )
        if not cuda_ok and force_cpu == "false" and device == "cpu":
            hint = (
                "On Windows, plain `pip install -e .` often installs CPU-only torch from PyPI; "
                "use `uv sync` or reinstall torch from the PyTorch CUDA index "
                "(see README: pip install torch --index-url https://download.pytorch.org/whl/cu126)."
            )
            if sys.platform == "win32":
                logger.warning(
                    "CUDA is off in this interpreter (%s) — %s",
                    sys.executable,
                    hint,
                )
            else:
                logger.warning(
                    "CUDA is off in this interpreter (%s) — usually CPU-only PyTorch or wrong venv.",
                    sys.executable,
                )

        reduce_gpu_memory = os.environ.get("BUZZ_REDUCE_GPU_MEMORY", "false") != "false" or os.environ.get(
            "BUZZMINI_REDUCE_VRAM", ""
        ).lower() in ("1", "true", "yes")
        compute_type = "default"
        if reduce_gpu_memory:
            compute_type = "int8" if device == "cpu" else "int8_float16"
            logger.debug("Using %s for reduced memory", compute_type)

        logger.info(
            "Loading faster-whisper model=%s device=%s compute_type=%s",
            self.model_size_or_path,
            device,
            compute_type,
        )
        self._model = faster_whisper.WhisperModel(
            model_size_or_path=self.model_size_or_path,
            download_root=model_root_dir,
            device=device,
            compute_type=compute_type,
            cpu_threads=max(1, (os.cpu_count() or 8) // 2),
        )

    def transcribe(self, audio_float32: np.ndarray, sample_rate: int, language: str | None) -> str:
        if self._model is None:
            raise RuntimeError("WhisperEngine.load() was not called")

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
