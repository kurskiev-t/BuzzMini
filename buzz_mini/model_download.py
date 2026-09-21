"""Download faster-whisper snapshots: GitHub Release mirror first, Hugging Face fallback.

The GitHub mirror (tag ``models-v1``) exists because Hugging Face is
unreachable from some networks — the HF request then hangs on "Connecting…"
with no error. See ``tools/make_model_assets.ps1`` for how mirror zips are made.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import multiprocessing
import os
import queue
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from buzz_mini.models_catalog import (
    ALLOW_PATTERNS,
    DOWNLOAD_COMPLETE_MARKER,
    GITHUB_MODELS_REPO,
    GITHUB_MODELS_TAG,
    github_asset_name,
    github_manifest_url,
    github_snapshot_dir,
)

logger = logging.getLogger(__name__)

# Hugging Face connect/read timeouts (seconds). Override with env if needed.
_HF_ETAG_TIMEOUT = int(os.environ.get("BUZZMINI_HF_ETAG_TIMEOUT", "30"))
_HF_DOWNLOAD_TIMEOUT = int(os.environ.get("BUZZMINI_HF_DOWNLOAD_TIMEOUT", "60"))
# No new progress after "Connecting…" → treat HF as unreachable (frozen exe used to hang forever).
_HF_STALL_S = int(os.environ.get("BUZZMINI_HF_STALL_S", "90"))
# HTTP chunk size for HF file downloads (MB). huggingface_hub defaults to 10 MB,
# which means one progress event per 10 MB — visibly steppy. 1 MB keeps the UI
# lively; per-chunk overhead is negligible (queue emits stay throttled).
_HF_CHUNK_MB = float(os.environ.get("BUZZMINI_HF_CHUNK_MB", "1") or 1)


def configure_ssl_certs() -> None:
    """Point OpenSSL/requests at certifi's CA bundle (needed in a frozen exe)."""
    try:
        import certifi

        ca = certifi.where()
    except Exception as exc:
        logger.warning("certifi unavailable: %s", exc)
        return
    if not ca or not os.path.isfile(ca):
        logger.warning("CA bundle missing at %s — HTTPS downloads may hang or fail", ca)
        return
    # In a frozen exe the inherited env may point at a missing bundle — force it.
    if getattr(sys, "frozen", False):
        os.environ["SSL_CERT_FILE"] = ca
        os.environ["REQUESTS_CA_BUNDLE"] = ca
        os.environ["CURL_CA_BUNDLE"] = ca
    else:
        os.environ.setdefault("SSL_CERT_FILE", ca)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ca)
        os.environ.setdefault("CURL_CA_BUNDLE", ca)
    logger.info("SSL CA bundle: %s", ca)


def _stream_broken(stream: object) -> bool:
    if stream is None:
        return True
    try:
        stream.write("")  # type: ignore[union-attr]
    except Exception:
        return True
    return False


def _ensure_stdio() -> None:
    """Windowed (noconsole) PyInstaller children often have stdout/stderr = None."""
    try:
        devnull = open(os.devnull, "w", encoding="utf-8", errors="replace")
    except OSError:
        return
    if _stream_broken(sys.stdout):
        sys.stdout = devnull  # type: ignore[assignment]
    if _stream_broken(sys.stderr):
        sys.stderr = devnull  # type: ignore[assignment]


class _DownloadCancelled(RuntimeError):
    pass


def _format_rate(bytes_per_sec: float) -> str:
    if not math.isfinite(bytes_per_sec) or bytes_per_sec < 0:
        return "…/sec"
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f} B/sec"
    kb = bytes_per_sec / 1024.0
    if kb < 1024:
        return f"{kb:.0f} kb/sec"
    return f"{kb / 1024.0:.1f} MB/sec"


def _format_eta(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0:
        return "…"
    total = int(seconds + 0.5)
    if total < 60:
        return f"{total} sec"
    mins, secs = divmod(total, 60)
    if mins < 60:
        return f"{mins} min : {secs} sec"
    hours, mins = divmod(mins, 60)
    return f"{hours} h {mins} min"


def format_download_status(
    name: str,
    received: int,
    total: Optional[int],
    started_at: float,
    now: Optional[float] = None,
) -> tuple[str, float]:
    """Caption (rate + ETA + MB) and bar fraction 0..1. Percent lives only on the bar."""
    label = (name or "file").strip() or "file"
    t = now if now is not None else time.monotonic()
    elapsed = max(t - started_at, 1e-3)
    received_n = max(0, int(received))
    rate = received_n / elapsed
    parts = [f"Downloading: {label}", _format_rate(rate)]
    frac = -1.0
    if total is not None and total > 0:
        tot = int(total)
        frac = min(1.0, max(0.0, received_n / tot))
        remaining = max(0, tot - received_n)
        if remaining > 0 and rate >= 1.0:
            parts.append(f"ETA {_format_eta(remaining / rate)}")
        elif remaining > 0:
            parts.append("ETA …")
        parts.append(f"({received_n / 1048576:.1f}/{tot / 1048576:.1f} MB)")
    else:
        parts.append(f"({received_n / 1048576:.1f} MB)")
    return " * ".join(parts), frac


def _fetch_github_manifest(timeout: int = 30) -> dict | None:
    """Return models.json dict or None (mirror without manifest still usable)."""
    url = github_manifest_url()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BuzzMini"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if getattr(resp, "status", 200) != 200:
                return None
            # NB: utf-8-sig — tools/make_model_assets.ps1 на Windows PowerShell 5.1
            # пишет models.json с BOM, чистый utf-8 на нём падает с "Unexpected UTF-8 BOM".
            return json.loads(resp.read().decode("utf-8-sig"))
    except Exception as exc:
        logger.info("GitHub models manifest unavailable (%s): %s", url, exc)
        return None


def _download_github_model(
    model_id: str,
    cache_dir: str,
    emit_progress: Callable[..., None],
    is_cancelled: Callable[[], bool],
    timeout: int = 60,
) -> str:
    """Download + unpack mirror zip into <cache_dir>/github-models/<id>/."""
    manifest = _fetch_github_manifest()
    assets = (manifest or {}).get("assets", {}) if isinstance(manifest, dict) else {}
    hashes = (manifest or {}).get("sha256", {}) if isinstance(manifest, dict) else {}
    asset = assets.get(model_id, github_asset_name(model_id))
    expected_sha = (hashes.get(model_id, "") or "").lower()
    base = f"https://github.com/{GITHUB_MODELS_REPO}/releases/download/{GITHUB_MODELS_TAG}/"
    url = base + asset

    emit_progress(f"Downloading from GitHub mirror ({asset})…", -1.0)
    logger.info("GitHub mirror download model=%s url=%s", model_id, url)

    fd, tmp_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BuzzMini"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = resp.headers.get("Content-Length")
            total_n = int(total) if total and total.isdigit() else None
            received = 0
            last_emit = 0.0
            started = time.monotonic()
            with open(tmp_path, "wb") as fh:
                while True:
                    if is_cancelled():
                        raise _DownloadCancelled("cancelled by user")
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
                    received += len(chunk)
                    now = time.monotonic()
                    if now - last_emit >= 0.3:
                        last_emit = now
                        text, frac = format_download_status(asset, received, total_n, started, now)
                        emit_progress(text, frac)
            if received:
                text, frac = format_download_status(
                    asset, received, total_n, started, time.monotonic()
                )
                emit_progress(text, frac)
        if expected_sha:
            emit_progress("Verifying checksum…", 1.0)
            digest = hashlib.sha256()
            with open(tmp_path, "rb") as fh:
                for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected_sha:
                raise RuntimeError("SHA-256 mismatch for mirror zip (corrupt download?)")
        dest = github_snapshot_dir(model_id, cache_dir)
        shutil.rmtree(dest, ignore_errors=True)
        os.makedirs(dest, exist_ok=True)
        emit_progress("Unpacking model…", 1.0)
        with zipfile.ZipFile(tmp_path) as zf:
            zf.extractall(dest)
        try:
            open(os.path.join(dest, DOWNLOAD_COMPLETE_MARKER), "w").close()
        except OSError:
            pass
        logger.info("GitHub mirror download finished model=%s path=%s", model_id, dest)
        return dest
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


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
        _ensure_stdio()
        configure_ssl_certs()
        os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", str(etag_timeout))
        os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", str(_HF_DOWNLOAD_TIMEOUT))

        # Apply Windows symlink fallback for HF cache (parent imports this module; child must too).
        import buzz_mini.models_catalog  # noqa: F401

        import huggingface_hub
        # NB: tqdm.std, not tqdm.auto — auto probes for notebooks/consoles and
        # touches sys.stdout, which is missing/broken in a windowed frozen child.
        from tqdm.std import tqdm as tqdm_base

        throttle_s = 0.2
        last_emit = [0.0]
        files_state = {"done": 0, "total": 0}

        def _emit_files(desc: str, n: int, total: Optional[int]) -> None:
            d = desc.strip() or "Downloading"
            frac: Optional[float] = None
            if total is not None and total > 0:
                files_state["done"] = n
                files_state["total"] = int(total)
                frac = min(1.0, max(0.0, n / total))
                text = f"{d} * file {n}/{int(total)}"
            else:
                text = d
            _queue_text(text, frac)

        def _emit_bytes(desc: str, n: int, total: Optional[int], started_at: float) -> None:
            d = desc.strip() or "Downloading"
            text, frac = format_download_status(d, n, total, started_at)
            if files_state["total"]:
                text += (
                    f" * file {min(files_state['done'] + 1, files_state['total'])}"
                    f"/{files_state['total']}"
                )
            _queue_text(text, frac if frac >= 0 else None)

        def _queue_text(text: str, frac: Optional[float]) -> None:
            try:
                progress_queue.put_nowait(("prog", text, frac))
            except Exception:
                pass

        try:
            progress_queue.put_nowait(("prog", "Connecting to Hugging Face…", None))
        except Exception:
            pass

        class ReporterTQDM(tqdm_base):
            """Progress via *progress_queue* only — never write bars (noconsole deadlock)."""

            def __init__(self, *args, **kwargs):
                kwargs.setdefault("file", sys.stderr)
                # NB: no disable=True here — tqdm.update() early-returns when
                # disabled and self.n would never advance, killing our queue
                # progress. display() below already suppresses all rendering.
                super().__init__(*args, **kwargs)
                # Set by _patch_file_progress for per-file byte bars (vs the
                # outer "Fetching N files" bar that snapshot_download makes).
                self._buzz_is_bytes = False
                self._buzz_t0 = time.monotonic()

            def display(self, *args, **kwargs):
                return None

            def close(self):
                try:
                    if self._buzz_is_bytes:
                        tot = self.total
                        tot_i = int(tot) if tot is not None else None
                        _emit_bytes(
                            self.desc or "",
                            int(self.n),
                            tot_i,
                            getattr(self, "_buzz_t0", time.monotonic()),
                        )
                except Exception:
                    pass
                try:
                    super().close()
                except Exception:
                    pass

            def update(self, n: int = 1):
                ret = super().update(n)
                now = time.monotonic()
                if now - last_emit[0] >= throttle_s:
                    last_emit[0] = now
                    tot = self.total
                    tot_i = int(tot) if tot is not None else None
                    if self._buzz_is_bytes:
                        _emit_bytes(
                            self.desc or "",
                            int(self.n),
                            tot_i,
                            getattr(self, "_buzz_t0", time.monotonic()),
                        )
                    else:
                        _emit_files(self.desc or "", int(self.n), tot_i)
                return ret

        def _patch_file_progress() -> None:
            """Route per-file byte bars into *progress_queue*.

            ``snapshot_download(tqdm_class=...)`` only applies the class to the
            outer "Fetching N files" bar — each file's byte progress goes through
            ``huggingface_hub.file_download._get_progress_bar_context`` instead
            (see ``huggingface_hub/_snapshot_download.py``: "tqdm_class is not
            passed to each individual download"). Without this, a 145 MB file
            means minutes of silence and trips the stall detector.
            """
            try:
                from huggingface_hub import file_download as hf_file_download
            except Exception:
                return
            if getattr(hf_file_download, "_buzz_patched", False):
                return
            if not hasattr(hf_file_download, "_get_progress_bar_context"):
                return
            import contextlib

            @contextlib.contextmanager
            def _ctx(*, desc: str, total=None, initial: int = 0, **kwargs):
                bar = ReporterTQDM(desc=desc, total=total, initial=initial)
                bar._buzz_is_bytes = True
                try:
                    yield bar
                finally:
                    bar.close()

            try:
                hf_file_download._get_progress_bar_context = _ctx
                hf_file_download._buzz_patched = True
            except Exception:
                pass

        _patch_file_progress()

        try:
            from huggingface_hub import constants as hf_constants

            chunk_bytes = max(256 * 1024, int(_HF_CHUNK_MB * 1048576))
            hf_constants.DOWNLOAD_CHUNK_SIZE = chunk_bytes
        except Exception:
            pass

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
            progress_queue.put_nowait(("prog", "Finishing…", 1.0))
        except Exception:
            pass
        result_queue.put(("ok", result))
    except Exception as exc:
        result_queue.put(("err", str(exc)))


class DownloadSignals(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    # Text + bar fraction in ONE signal so label and bar always match
    # (two separate signals race in the GUI event queue: "42%" bar vs "43%" text).
    # frac: 0..1 = determinate, negative = indeterminate (busy).
    progress = pyqtSignal(str, float)
    aborted = pyqtSignal()


class ModelSnapshotDownloadTask(QRunnable):
    """Runs GitHub-mirror download first, then HF snapshot_download like Buzz."""

    def __init__(self, repo_id: str, cache_dir: str, model_id: str | None = None) -> None:
        super().__init__()
        self.repo_id = repo_id
        self.cache_dir = cache_dir
        self.model_id = model_id
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
    def _drain_progress(
        progress_queue: multiprocessing.Queue,
        emit_progress: Callable[[str, float], None],
    ) -> bool:
        got = False
        try:
            while True:
                item = progress_queue.get_nowait()
                kind = item[0] if len(item) > 0 else None
                if kind == "prog":
                    got = True
                    text = str(item[1]) if len(item) > 1 else ""
                    raw = item[2] if len(item) > 2 else None
                    try:
                        frac = float(raw) if raw is not None else -1.0
                    except (TypeError, ValueError):
                        frac = -1.0
                    if not math.isfinite(frac):
                        frac = -1.0
                    emit_progress(text, frac)
        except queue.Empty:
            pass
        return got

    def run(self) -> None:
        try:
            self._run_impl()
        except Exception as exc:
            logger.exception("Model download task crashed repo=%s", self.repo_id)
            if self.stopped:
                self.signals.aborted.emit()
                return
            self.signals.error.emit(str(exc) or "Download failed (uncaught error).")

    def _run_impl(self) -> None:
        def emit_p(text: str, frac: float = -1.0) -> None:
            self.signals.progress.emit(text, frac)

        # 1) GitHub Release mirror (fast fail -> HF fallback, not an error).
        skip_github = os.environ.get("BUZZMINI_DISABLE_GITHUB_MIRROR", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if self.model_id and not skip_github:
            try:
                path = _download_github_model(
                    self.model_id,
                    self.cache_dir,
                    emit_p,
                    lambda: self.stopped,
                )
            except _DownloadCancelled:
                logger.info("GitHub mirror download aborted repo=%s", self.repo_id)
                self.signals.aborted.emit()
                return
            except Exception as exc:
                if self.stopped:
                    self.signals.aborted.emit()
                    return
                logger.warning("GitHub mirror failed (%s), falling back to Hugging Face", exc)
                emit_p("GitHub mirror unavailable, trying Hugging Face…")
            else:
                if self.stopped:
                    self.signals.aborted.emit()
                    return
                logger.info("Model download finished repo=%s path=%s", self.repo_id, path)
                self.signals.finished.emit(str(path))
                return

        # 2) Hugging Face (original Buzz-style path).
        configure_ssl_certs()
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
                _HF_ETAG_TIMEOUT,
                max_workers,
            ),
            daemon=True,
        )
        self._register_process(proc)
        proc.start()

        last_progress_at = time.monotonic()
        while proc.is_alive():
            if self._drain_progress(progress_queue, emit_p):
                last_progress_at = time.monotonic()
            if self.stopped:
                if proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=120)
                self._drain_progress(progress_queue, emit_p)
                logger.info("Model download aborted repo=%s", self.repo_id)
                self.signals.aborted.emit()
                return
            if time.monotonic() - last_progress_at >= _HF_STALL_S:
                logger.error(
                    "Hugging Face download stalled for %ss repo=%s — terminating worker",
                    _HF_STALL_S,
                    self.repo_id,
                )
                if proc.is_alive():
                    proc.terminate()
                    proc.join(timeout=30)
                self._drain_progress(progress_queue, emit_p)
                self.signals.error.emit(
                    f"Hugging Face did not respond within {_HF_STALL_S} seconds "
                    "(connection hung). Check the network, VPN, or firewall for BuzzMini.exe."
                )
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
