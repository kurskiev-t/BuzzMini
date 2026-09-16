from __future__ import annotations

import logging
import os

from buzz_mini.backends.gpu_detect import (
    has_amd_adapter,
    has_nvidia_adapter,
    win32_video_adapter_names,
)

logger = logging.getLogger(__name__)

BackendName = str  # "cuda" | "vulkan" | "cpu"


def resolve_backend_name() -> BackendName:
    """Choose transcription stack from BUZZMINI_BACKEND (cuda | vulkan | cpu | auto)."""
    raw = os.environ.get("BUZZMINI_BACKEND", "").strip().lower()
    if raw in ("cuda", "vulkan", "cpu"):
        logger.info("BUZZMINI_BACKEND=%s", raw)
        return raw
    if raw and raw != "auto":
        logger.warning("Unknown BUZZMINI_BACKEND=%r — using auto", raw)
    chosen = _auto_backend_name()
    logger.info("BUZZMINI_BACKEND=auto -> %s", chosen)
    return chosen


def _auto_backend_name() -> BackendName:
    names = win32_video_adapter_names()
    if has_nvidia_adapter(names):
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
    if _whisper_cli_configured() and (has_amd_adapter(names) or not has_nvidia_adapter(names)):
        return "vulkan"
    return "cpu"


def _whisper_cli_configured() -> bool:
    cli = os.environ.get("BUZZMINI_WHISPER_CLI", "").strip()
    ggml = os.environ.get("BUZZMINI_GGML_MODEL", "").strip()
    return bool(cli and ggml and os.path.isfile(cli) and os.path.isfile(ggml))
