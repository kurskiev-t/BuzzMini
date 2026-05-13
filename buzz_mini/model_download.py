"""Download faster-whisper HF snapshots in a subprocess (Buzz-style; cancellable)."""

from __future__ import annotations

import multiprocessing
import os
import queue
import sys
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from buzz_mini.models_catalog import ALLOW_PATTERNS, DOWNLOAD_COMPLETE_MARKER


def _snapshot_download_worker(
    result_queue: multiprocessing.Queue,
    repo_id: str,
    patterns: list[str],
    cache_dir: str,
    etag_timeout: int,
    max_workers: int,
) -> None:
    try:
        import huggingface_hub

        result = huggingface_hub.snapshot_download(
            repo_id,
            allow_patterns=patterns,
            cache_dir=cache_dir,
            etag_timeout=etag_timeout,
            max_workers=max_workers,
        )
        try:
            open(os.path.join(result, DOWNLOAD_COMPLETE_MARKER), "w").close()
        except OSError:
            pass
        result_queue.put(("ok", result))
    except Exception as exc:
        result_queue.put(("err", str(exc)))


class DownloadSignals(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)


class ModelSnapshotDownloadTask(QRunnable):
    """Runs Hugging Face snapshot_download like Buzz `download_from_huggingface`."""

    def __init__(self, repo_id: str, cache_dir: str) -> None:
        super().__init__()
        self.repo_id = repo_id
        self.cache_dir = cache_dir
        self.signals = DownloadSignals()
        self.stopped = False
        self._proc: Optional[multiprocessing.Process] = None

    def _register_process(self, proc: multiprocessing.Process) -> None:
        self._proc = proc

    def cancel(self) -> None:
        self.stopped = True
        if self._proc is not None and self._proc.is_alive():
            self._proc.terminate()
            self._proc = None

    def run(self) -> None:
        max_workers = 1 if sys.platform == "win32" else 8
        result_queue: multiprocessing.Queue = multiprocessing.Queue()
        proc = multiprocessing.Process(
            target=_snapshot_download_worker,
            args=(
                result_queue,
                self.repo_id,
                ALLOW_PATTERNS,
                self.cache_dir,
                60,
                max_workers,
            ),
            daemon=True,
        )
        self._register_process(proc)
        proc.start()
        proc.join()

        if self.stopped:
            return

        if proc.exitcode != 0:
            self.signals.error.emit("Download process failed")
            return

        try:
            status, payload = result_queue.get_nowait()
        except queue.Empty:
            self.signals.error.emit("Download returned no result")
            return

        if status != "ok":
            self.signals.error.emit(str(payload))
            return

        self.signals.finished.emit(str(payload))
