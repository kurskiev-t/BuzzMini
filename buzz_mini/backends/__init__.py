"""Transcription backends (faster-whisper CUDA/CPU, whisper.cpp Vulkan)."""

from buzz_mini.backends.base import TranscriptionBackend
from buzz_mini.backends.select import resolve_backend_name

__all__ = ["TranscriptionBackend", "resolve_backend_name"]
