"""
Faster Whisper model catalog + Hugging Face repos (aligned with Buzz `download_faster_whisper_model`).

Offline / Colab: download a CTranslate2 snapshot elsewhere, copy the folder that contains
``model.bin`` (+ ``config.json``, tokenizer, …) onto this PC, then point the app at it::

    set BUZZMINI_MODEL=C:\\path\\to\\that\\folder

Or set the same path in QSettings via replacing selected model id — ``find_local_snapshot``
accepts an absolute path to a usable snapshot directory.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

from buzz_mini.engine import _resolve_download_root

logger = logging.getLogger(__name__)

# Same marker as Buzz — shared cache stays consistent.
DOWNLOAD_COMPLETE_MARKER = ".buzz_complete"

ALLOW_PATTERNS = [
    "model.bin",
    "pytorch_model.bin",
    "config.json",
    "preprocessor_config.json",
    "tokenizer.json",
    "vocabulary.*",
]


@dataclass(frozen=True)
class ModelEntry:
    model_id: str
    title: str


# Order matches Buzz “Whisper” group (minus custom / lumii).
MODEL_ENTRIES: tuple[ModelEntry, ...] = (
    ModelEntry("tiny", "Tiny"),
    ModelEntry("tiny.en", "Tiny.En"),
    ModelEntry("base", "Base"),
    ModelEntry("base.en", "Base.En"),
    ModelEntry("small", "Small"),
    ModelEntry("small.en", "Small.En"),
    ModelEntry("medium", "Medium"),
    ModelEntry("medium.en", "Medium.En"),
    ModelEntry("large-v1", "Large"),
    ModelEntry("large-v2", "Large-V2"),
    ModelEntry("large-v3", "Large-V3"),
    ModelEntry("large-v3-turbo", "Large-V3-Turbo"),
)


def repo_id_for_model(model_id: str) -> str:
    if model_id == "large-v3-turbo":
        return "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
    return f"Systran/faster-whisper-{model_id}"


def entry_for_id(model_id: str) -> ModelEntry | None:
    for e in MODEL_ENTRIES:
        if e.model_id == model_id:
            return e
    return None


def _expanded_path(model_id: str) -> str:
    return os.path.normpath(os.path.expanduser(os.path.expandvars(model_id.strip().strip("\"'"))))


def is_local_snapshot_directory(model_id: str) -> bool:
    """True if *model_id* is (or expands to) a directory that already contains model weights."""
    p = _expanded_path(model_id)
    return os.path.isdir(p) and _snapshot_usable(p)


def title_for_id(model_id: str) -> str:
    if is_local_snapshot_directory(model_id):
        base = os.path.basename(_expanded_path(model_id))
        return base if base else model_id
    e = entry_for_id(model_id)
    return e.title if e else model_id


def _patch_hf_hub_windows_symlinks() -> None:
    if sys.platform != "win32":
        return
    try:
        import shutil as shutil_mod
        from pathlib import Path

        from huggingface_hub import file_download

        _original_create_symlink = file_download._create_symlink

        def _windows_create_symlink(src: Path, dst: Path, new_blob: bool = False) -> None:
            src = Path(src)
            dst = Path(dst)
            if dst.exists():
                if dst.is_symlink():
                    return
                if dst.is_file() and dst.stat().st_size == src.stat().st_size:
                    return
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                dst.unlink(missing_ok=True)
                os.symlink(src, dst)
                return
            except OSError:
                pass
            dst.unlink(missing_ok=True)
            shutil_mod.copy2(src, dst)

        file_download._create_symlink = _windows_create_symlink
    except Exception as exc:
        logger.debug("HF symlink patch skipped: %s", exc)


_patch_hf_hub_windows_symlinks()


def _snapshot_usable(snapshot_path: str) -> bool:
    """Installed if Buzz marker exists or core weights are present (HF cache without marker)."""
    if os.path.exists(os.path.join(snapshot_path, DOWNLOAD_COMPLETE_MARKER)):
        return True
    for name in ("model.bin", "pytorch_model.bin"):
        if os.path.exists(os.path.join(snapshot_path, name)):
            return True
    return False


def find_local_snapshot(model_id: str, download_root: str | None = None) -> str | None:
    """Return snapshot dir if the model is already on disk (HF cache or manual folder)."""
    local = _expanded_path(model_id)
    if os.path.isdir(local) and _snapshot_usable(local):
        logger.info("Local snapshot directory: %s", local)
        return local

    if entry_for_id(model_id) is None:
        return None

    download_root = download_root or _resolve_download_root()
    repo = repo_id_for_model(model_id)

    try:
        import huggingface_hub

        path = huggingface_hub.snapshot_download(
            repo_id=repo,
            allow_patterns=ALLOW_PATTERNS,
            local_files_only=True,
            cache_dir=download_root,
            etag_timeout=60,
        )
    except (FileNotFoundError, OSError, ValueError):
        return None
    except Exception:
        return None

    if not _snapshot_usable(path):
        return None
    return path


def delete_model_cache(model_id: str, download_root: str | None = None) -> None:
    """Remove HF cache folder for this repo, or the manual folder if *model_id* is a path."""
    snapshot = find_local_snapshot(model_id, download_root)
    if not snapshot:
        return
    if is_local_snapshot_directory(model_id):
        shutil.rmtree(snapshot, ignore_errors=True)
        return
    # Buzz: go up from snapshot file folder to shared repo cache root
    cache_chunk = os.path.dirname(os.path.dirname(snapshot))
    shutil.rmtree(cache_chunk, ignore_errors=True)


def open_snapshot_in_explorer(model_id: str, download_root: str | None = None) -> None:
    snapshot = find_local_snapshot(model_id, download_root)
    if not snapshot:
        return
    path = os.path.normpath(snapshot)
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)
