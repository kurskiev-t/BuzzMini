from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Optional

import numpy as np

from buzz_mini.whisper_common import WHISPER_SR, resample_linear

logger = logging.getLogger(__name__)


def default_whisper_cli_path() -> Path | None:
    """``third_party/whisper.cpp/build/bin/Release/whisper-cli.exe`` after tools/build_whispercpp_windows.ps1."""
    here = Path(__file__).resolve().parents[2]
    candidate = here / "third_party" / "whisper.cpp" / "build" / "bin" / "Release" / "whisper-cli.exe"
    if candidate.is_file():
        return candidate
    candidate = here / "third_party" / "whisper.cpp" / "build" / "bin" / "whisper-cli.exe"
    if candidate.is_file():
        return candidate
    return None


def resolve_whisper_cli() -> Path:
    raw = os.environ.get("BUZZMINI_WHISPER_CLI", "").strip()
    if raw:
        p = Path(raw)
        if p.is_file():
            return p
        raise FileNotFoundError(f"BUZZMINI_WHISPER_CLI not found: {raw}")
    found = default_whisper_cli_path()
    if found is not None:
        return found
    raise FileNotFoundError(
        "whisper-cli not found. Run tools/build_whispercpp_windows.ps1 or set BUZZMINI_WHISPER_CLI."
    )


def resolve_ggml_model() -> Path:
    raw = os.environ.get("BUZZMINI_GGML_MODEL", "").strip()
    if raw:
        p = Path(raw)
        if p.is_file():
            return p
        raise FileNotFoundError(f"BUZZMINI_GGML_MODEL not found: {raw}")
    here = Path(__file__).resolve().parents[2]
    for name in (
        "ggml-base.bin",
        "ggml-small.bin",
        "ggml-tiny.bin",
    ):
        candidate = here / "models" / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "No GGML model. Set BUZZMINI_GGML_MODEL or place ggml-*.bin under models/ "
        "(see tools/spike_whisper_vulkan.ps1)."
    )


class WhisperCppBackend:
    """whisper.cpp via whisper-cli subprocess (Vulkan when built with GGML_VULKAN)."""

    def __init__(self, model_size_or_path: Optional[str] = None) -> None:
        self.model_id = model_size_or_path or os.environ.get("BUZZMINI_MODEL", "large-v3-turbo")
        self._cli: Path | None = None
        self._ggml: Path | None = None
        self._ngl = int(os.environ.get("BUZZMINI_WHISPER_NGL", "99"))

    def set_model_id(self, model_id: str) -> None:
        self.model_id = model_id
        # HF model ids are not ggml paths; BUZZMINI_GGML_MODEL wins at load time.

    def unload(self) -> None:
        self._cli = None
        self._ggml = None

    def load(self) -> None:
        self._cli = resolve_whisper_cli()
        self._ggml = resolve_ggml_model()
        logger.info("whisper.cpp cli=%s ggml=%s ngl=%s", self._cli, self._ggml, self._ngl)

    def transcribe(self, audio_float32: np.ndarray, sample_rate: int, language: str | None) -> str:
        if self._cli is None or self._ggml is None:
            raise RuntimeError("WhisperCppBackend.load() was not called")

        mono = audio_float32.astype(np.float32, copy=False)
        if mono.ndim > 1:
            mono = mono.mean(axis=1)
        audio_in = resample_linear(mono, sample_rate, WHISPER_SR)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        try:
            self._write_wav(wav_path, audio_in, WHISPER_SR)
            cmd = [
                str(self._cli),
                "-m",
                str(self._ggml),
                "-f",
                wav_path,
                "-nt",
                "-ngl",
                str(self._ngl),
            ]
            if language:
                cmd.extend(["-l", language])
            logger.debug("whisper-cli: %s", " ".join(cmd))
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=int(os.environ.get("BUZZMINI_WHISPER_TIMEOUT", "600")),
                creationflags=creationflags,
            )
            if proc.returncode != 0:
                err = (proc.stderr or proc.stdout or "").strip()
                raise RuntimeError(f"whisper-cli failed ({proc.returncode}): {err[:2000]}")

            text = self._parse_cli_output(proc.stdout or "")
            if not text.strip():
                text = self._parse_cli_output(proc.stderr or "")
            return text.strip()
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass

    @staticmethod
    def _write_wav(path: str, samples: np.ndarray, sample_rate: int) -> None:
        pcm = np.clip(samples, -1.0, 1.0)
        ints = (pcm * 32767.0).astype(np.int16)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(ints.tobytes())

    @staticmethod
    def _parse_cli_output(stdout: str) -> str:
        lines: list[str] = []
        for line in stdout.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("[") and "]" in s[:20]:
                continue
            m = re.match(r"^\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}\s+(.*)$", s)
            if m:
                lines.append(m.group(1).strip())
                continue
            if s.startswith("--") or "whisper_" in s.lower():
                continue
            lines.append(s)
        return " ".join(lines).strip()
