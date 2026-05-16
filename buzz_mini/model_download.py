"""Download faster-whisper HF snapshots in a subprocess (Buzz-style; cancellable)."""

from __future__ import annotations

import logging
import multiprocessing
import os
import queue
import sys
import time
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from buzz_mini.models_catalog import ALLOW_PATTERNS, DOWNLOAD_COMPLETE_MARKER

logger = logging.getLogger(__name__)


def _snapshot_download_worker(
    result_queue: multiprocessing.Queue,
    progress_queue: multiprocessing.Queue,
    repo_id: str,
    patterns: list[str],
    cache_dir: str,
    etag_timeout: int,
    max_workers: int,
) -> None:
    """Runs in child process."""
    try:
        # Apply Windows symlink fallback for HF cache (parent imports this module; child must too).
        import buzz_mini.models_catalog  # noqa: F401

        import huggingface_hub
        from tqdm.auto import tqdm as tqdm_base

        throttle_s = 0.2
        last_emit = [0.0]

        def _emit(desc: str, n: int, total: Optional[int]) -> None:
            d = desc.strip() or "Downloading"
            if total is not None and total > 0:
                pct = min(100.0, 100.0 * n / total)
                text = f"{d} · {pct:.0f}% ({n}/{total} files)"
            else:
                text = d
            try:
                progress_queue.put_nowait(("prog", text))
            except Exception:
                pass

        try:
            progress_queue.put_nowait(("prog", "Connecting to Hugging Face…"))
        except Exception:
            pass

        class ReporterTQDM(tqdm_base):
            """Feed coarse file-level progress into *progress_queue* (from thread_map iterator)."""

            def update(self, n: int = 1):
                ret = super().update(n)
                now = time.monotonic()
                if now - last_emit[0] >= throttle_s:
                    last_emit[0] = now
                    tot = self.total
                    tot_i = int(tot) if tot is not None else None
                    _emit(self.desc or "", int(self.n), tot_i)
                return ret

        result = huggingface_hub.snapshot_download(
            repo_id,
            allow_patterns=patterns,
            cache_dir=cache_dir,
            etag_timeout=etag_timeout,
            max_workers=max_workers,
            tqdm_class=ReporterTQDM,
        )
        try:
            open(os.path.join(result, DOWNLOAD_COMPLETE_MARKER), "w").close()
        except OSError:
            pass
        try:
            progress_queue.put_nowait(("prog", "Finishing…"))
        except Exception:
            pass
        result_queue.put(("ok", result))
    except Exception as exc:
        result_queue.put(("err", str(exc)))


class DownloadSignals(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    aborted = pyqtSignal()


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

    @staticmethod
    def _drain_progress(progress_queue: multiprocessing.Queue, emit_progress: Callable[[str], None]) -> None:
        try:
            while True:
                kind, payload = progress_queue.get_nowait()
                if kind == "prog":
                    emit_progress(str(payload))
        except queue.Empty:
            pass

    def run(self) -> None:
        max_workers = 1 if sys.platform == "win32" else 8
        result_queue: multiprocessing.Queue = multiprocessing.Queue()
        progress_queue: multiprocessing.Queue = multiprocessing.Queue()

        logger.info("Starting HF snapshot download repo=%s cache_dir=%s", self.repo_id, self.cache_dir)

        proc = multiprocessing.Process(
            target=_snapshot_download_worker,
            args=(
                result_queue,
                progress_queue,
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

        emit_p = self.signals.progress.emit
        while proc.is_alive():
            self._drain_progress(progress_queue, emit_p)
            if self.stopped:
                if proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=120)
                self._drain_progress(progress_queue, emit_p)
                logger.info("Model download aborted repo=%s", self.repo_id)
                self.signals.aborted.emit()
                return
            proc.join(timeout=0.08)

        self._drain_progress(progress_queue, emit_p)

        if self.stopped:
            self.signals.aborted.emit()
            return

        if proc.exitcode != 0:
            msg = f"Download process failed (exit code {proc.exitcode})."
            logger.error("%s repo=%s", msg, self.repo_id)
            self.signals.error.emit(msg)
            return

        try:
            status, payload = result_queue.get_nowait()
        except queue.Empty:
            msg = "Download returned no result (empty queue)."
            logger.error("%s repo=%s exit=%s", msg, self.repo_id, proc.exitcode)
            self.signals.error.emit(msg)
            return

        if status != "ok":
            err = str(payload)
            logger.error("Model download failed repo=%s: %s", self.repo_id, err)
            self.signals.error.emit(err)
            return

        logger.info("Model download finished repo=%s path=%s", self.repo_id, payload)
        self.signals.finished.emit(str(payload))
