"""
Qt tray app + global push-to-talk (default: Left Ctrl + Space) + minimal overlay.
Optional: BUZZMINI_PTT_CHORD (e.g. ctrl_l+space, ctrl_r+win, ctrl+space like Handy on Windows).
Paste uses clipboard + modifier+V via pynput (Handy-style: delay after clipboard, VK on Windows).
BUZZMINI_PASTE_DELAY_MS (default 60) waits for the OS clipboard before sending keys.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QGuiApplication, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QMenu,
    QStyle,
    QSystemTrayIcon,
)

from buzz_mini.audio_ptt import PTTCapture
from buzz_mini.engine import WhisperEngine, _resolve_download_root
from buzz_mini.main_window import BuzzMainWindow, MainTab
from buzz_mini.models_catalog import find_local_snapshot, title_for_id
from buzz_mini.overlay import RecordingOverlay
from buzz_mini.ptt_chord import effective_ptt_chord_raw, parse_ptt_chord_raw
from buzz_mini.settings_store import DictateSettings

logger = logging.getLogger(__name__)


def _load_tray_icon() -> QIcon | None:
    """``assets/tray.png`` at repository root, if present."""
    p = Path(__file__).resolve().parent.parent / "assets" / "tray.png"
    if not p.is_file():
        return None
    pm = QPixmap(str(p))
    if pm.isNull():
        return None
    return QIcon(pm)


def _effective_input_device(settings: DictateSettings) -> Optional[int]:
    """BUZZMINI_AUDIO_DEVICE (int) overrides Settings."""
    raw = os.environ.get("BUZZMINI_AUDIO_DEVICE", "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            logger.warning("BUZZMINI_AUDIO_DEVICE must be an integer; ignoring")
    return settings.input_device_index()


def _parse_language() -> Optional[str]:
    lang = os.environ.get("BUZZMINI_LANGUAGE", "").strip()
    return lang or None


def _key_match(event: object, target: object) -> bool:
    """True if pynput key event matches target (handles vk quirks on Windows)."""
    if event is None:
        return False
    if event == target:
        return True
    try:
        vk_e = getattr(event, "vk", None)
        vk_t = getattr(target, "vk", None)
        if vk_e is not None and vk_t is not None and vk_e == vk_t:
            return True
    except Exception:
        pass
    return False


class HotkeyBridge(QObject):
    """Marshal pynput callbacks onto the Qt thread via queued signals."""

    ptt_down = pyqtSignal()
    ptt_up = pyqtSignal()


class LoadWorker(QObject):
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, engine: WhisperEngine, download_root: str) -> None:
        super().__init__()
        self._engine = engine
        self._download_root = download_root

    @pyqtSlot()
    def run(self) -> None:
        th = QThread.currentThread()
        try:
            if th.isInterruptionRequested():
                return
            mid = self._engine.model_size_or_path
            if find_local_snapshot(mid, self._download_root) is None:
                if not th.isInterruptionRequested():
                    self.failed.emit(
                        "Model is not downloaded yet.\nOpen Buzz Mini → Models tab → Download."
                    )
                return
            if th.isInterruptionRequested():
                return
            self._engine.load()
            if th.isInterruptionRequested():
                self._engine.unload()
                return
            self.finished.emit()
        except Exception as e:
            if th.isInterruptionRequested():
                return
            logger.exception("Model load failed")
            self.failed.emit(str(e))


class DictateController(QObject):
    """Owns capture lifecycle and transcription scheduling."""

    transcribe_done = pyqtSignal(str)
    transcribe_failed = pyqtSignal(str)
    overlay_listening = pyqtSignal()
    overlay_transcribing = pyqtSignal()
    overlay_hide = pyqtSignal()

    def __init__(self, engine: WhisperEngine, tray: QSystemTrayIcon, settings: DictateSettings) -> None:
        super().__init__()
        self._engine = engine
        self._tray = tray
        self._settings = settings
        self._capture = PTTCapture(_effective_input_device(settings))
        self._recording = False
        self._busy = False
        self._ready = False

    def refresh_input_device(self) -> None:
        """Re-read device from settings / env (call after Settings OK)."""
        self._capture.set_input_device(_effective_input_device(self._settings))

    def set_ready(self, ok: bool) -> None:
        self._ready = ok

    def is_ready(self) -> bool:
        return self._ready

    def shutdown(self) -> None:
        """Stop capture and ignore further hotkey actions (called before process exit)."""
        self._ready = False
        if self._recording:
            try:
                self._capture.stop()
            except Exception:
                logger.exception("Capture stop during shutdown")
            self._recording = False

    @pyqtSlot()
    def on_ptt_down(self) -> None:
        if not self._ready or self._busy:
            return
        if self._recording:
            return
        self._recording = True
        try:
            self._capture.set_input_device(_effective_input_device(self._settings))
            self._capture.start()
            self.overlay_listening.emit()
        except Exception as e:
            logger.exception("Audio start failed")
            self._recording = False
            self._tray.showMessage("Buzz Mini", str(e), QSystemTrayIcon.MessageIcon.Warning)

    @pyqtSlot()
    def on_ptt_up(self) -> None:
        if not self._recording:
            return
        self._recording = False
        self.overlay_transcribing.emit()
        samples, sr = self._capture.stop()
        if samples.size < max(int(0.12 * sr), 800):
            logger.debug("Drop short utterance (%s samples)", samples.size)
            self.overlay_hide.emit()
            return
        if self._busy:
            self.overlay_hide.emit()
            return
        self._busy = True
        lang = _parse_language()

        def work() -> None:
            try:
                text = self._engine.transcribe(samples, sr, lang)
                self.transcribe_done.emit(text)
            except Exception as e:
                logger.exception("Transcribe failed")
                self.transcribe_failed.emit(str(e))
            finally:
                self._busy = False

        threading.Thread(target=work, name="transcribe", daemon=True).start()


def _paste_via_clipboard(app: QApplication, text: str) -> None:
    if not text:
        return
    raw = os.environ.get("BUZZMINI_PASTE_DELAY_MS", "60").strip()
    try:
        delay_ms = max(0, int(raw))
    except ValueError:
        delay_ms = 60

    cb = QGuiApplication.clipboard()
    cb.setText(text)
    app.processEvents()
    if delay_ms:
        time.sleep(delay_ms / 1000.0)

    from pynput.keyboard import Controller, Key, KeyCode

    ctrl = Controller()
    try:
        if sys.platform == "darwin":
            ctrl.press(Key.cmd)
            ctrl.press("v")
            ctrl.release("v")
            ctrl.release(Key.cmd)
        elif sys.platform == "win32":
            # VK_V (0x56): layout-independent, matches Handy/enigo on Windows.
            v_key = KeyCode.from_vk(0x56)
            ctrl.press(Key.ctrl)
            ctrl.press(v_key)
            ctrl.release(v_key)
            time.sleep(0.1)
            ctrl.release(Key.ctrl)
        else:
            ctrl.press(Key.ctrl)
            ctrl.press("v")
            ctrl.release("v")
            ctrl.release(Key.ctrl)
    except Exception:
        logger.exception("Paste simulation failed — text is on the clipboard")


def _start_hotkey_listener(bridge: HotkeyBridge, ctrl_key: object, partner_key: object) -> object:
    """Start global chord listener (both keys down = PTT). Return listener (call `.stop()` before exit)."""
    from pynput import keyboard

    ctrl_down = False
    partner_down = False
    chord_active = False

    def on_press(key: keyboard.Key | keyboard.KeyCode | None) -> None:
        nonlocal ctrl_down, partner_down, chord_active
        if _key_match(key, ctrl_key):
            ctrl_down = True
        if _key_match(key, partner_key):
            partner_down = True
        if ctrl_down and partner_down and not chord_active:
            chord_active = True
            bridge.ptt_down.emit()

    def on_release(key: keyboard.Key | keyboard.KeyCode | None) -> None:
        nonlocal ctrl_down, partner_down, chord_active
        if _key_match(key, ctrl_key):
            ctrl_down = False
        if _key_match(key, partner_key):
            partner_down = False
        if chord_active and not (ctrl_down and partner_down):
            chord_active = False
            bridge.ptt_up.emit()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()
    return listener


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("BUZZMINI_LOG_LEVEL", "INFO"),
        format="%(levelname)s %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    settings = DictateSettings()
    download_root = _resolve_download_root()
    os.makedirs(download_root, exist_ok=True)

    model_id = os.environ.get("BUZZMINI_MODEL", "").strip() or settings.selected_model_id()
    settings.set_selected_model_id(model_id)

    engine = WhisperEngine(model_size_or_path=model_id)
    tray = QSystemTrayIcon(app)
    _ico = _load_tray_icon()
    if _ico is not None:
        app.setWindowIcon(_ico)
        tray.setIcon(_ico)
    else:
        tray.setIcon(app.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
    tray.setToolTip("Buzz Mini — loading model…")

    overlay = RecordingOverlay()
    controller = DictateController(engine, tray, settings)
    bridge = HotkeyBridge()

    hotkey_listener = None
    hotkey_started = False

    _ctrl_ptt, _partner_ptt, ptt_chord_label = parse_ptt_chord_raw(effective_ptt_chord_raw(settings))
    logger.info("Push-to-talk: %s (Tray → Settings tab, or BUZZMINI_PTT_CHORD)", ptt_chord_label)

    menu = QMenu()
    open_action = QAction("Open Buzz Mini")
    models_action = QAction("Models")
    settings_action = QAction("Settings")
    logs_action = QAction("Logs")
    unload_action = QAction("Unload model")
    donate_action = QAction("Donate — Донат")
    quit_action = QAction("Quit")
    menu.addAction(open_action)
    menu.addAction(models_action)
    menu.addAction(settings_action)
    menu.addAction(logs_action)
    menu.addSeparator()
    menu.addAction(unload_action)
    menu.addSeparator()
    menu.addAction(donate_action)
    menu.addSeparator()
    menu.addAction(quit_action)
    tray.setContextMenu(menu)
    tray.show()

    main_win = BuzzMainWindow(settings, download_root)
    main_win.hide()

    def _show_main(tab: MainTab | None = None) -> None:
        if tab is not None:
            main_win.show_tab(tab)
        else:
            main_win.show()
            main_win.raise_()
            main_win.activateWindow()

    def on_tray_activated(reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            _show_main(MainTab.MODELS)

    tray.activated.connect(on_tray_activated)

    def refresh_ptt_chord_from_settings() -> None:
        nonlocal _ctrl_ptt, _partner_ptt, ptt_chord_label
        _ctrl_ptt, _partner_ptt, ptt_chord_label = parse_ptt_chord_raw(effective_ptt_chord_raw(settings))
        logger.info("Push-to-talk: %s", ptt_chord_label)

    def stop_hotkey_listener() -> None:
        nonlocal hotkey_listener
        if hotkey_listener is not None:
            try:
                hotkey_listener.stop()
            except Exception:
                logger.exception("Hotkey listener stop")
            hotkey_listener = None

    def attach_hotkey_listener() -> None:
        nonlocal hotkey_listener
        stop_hotkey_listener()
        if not controller.is_ready():
            return
        hotkey_listener = _start_hotkey_listener(bridge, _ctrl_ptt, _partner_ptt)
        logger.info("Hotkey listener on GUI thread")

    def update_tooltip_ready() -> None:
        mid = settings.selected_model_id()
        tray.setToolTip(f"Buzz Mini — {title_for_id(mid)} — hold {ptt_chord_label}")

    def on_load_success() -> None:
        nonlocal hotkey_started
        refresh_ptt_chord_from_settings()
        controller.set_ready(True)
        update_tooltip_ready()
        first = not hotkey_started
        hotkey_started = True
        attach_hotkey_listener()
        main_win.models_panel().refresh_after_external_model_change()
        if first:
            tray.showMessage(
                "Buzz Mini",
                f"Ready — {title_for_id(settings.selected_model_id())}. Hold {ptt_chord_label} to dictate.",
                QSystemTrayIcon.MessageIcon.Information,
                3500,
            )

    def on_load_failed(msg: str) -> None:
        nonlocal hotkey_started
        controller.set_ready(False)
        stop_hotkey_listener()
        hotkey_started = False
        tray.setToolTip("Buzz Mini — model not loaded")
        tray.showMessage("Buzz Mini", msg, QSystemTrayIcon.MessageIcon.Warning, 8000)

    load_thread: Optional[QThread] = None

    class _LoadUiRelay(QObject):
        """Marshals load worker signals onto the GUI thread (pynput must start there)."""

        @pyqtSlot()
        def on_ok(self) -> None:
            on_load_success()

        @pyqtSlot(str)
        def on_fail(self, msg: str) -> None:
            on_load_failed(msg)

    load_ui_relay = _LoadUiRelay(app)

    def schedule_load() -> None:
        nonlocal load_thread, hotkey_started
        controller.set_ready(False)
        stop_hotkey_listener()
        hotkey_started = False
        tray.setToolTip("Buzz Mini — loading model…")
        engine.unload()
        engine.set_model_id(settings.selected_model_id())

        lt = QThread()
        ld = LoadWorker(engine, download_root)
        ld.moveToThread(lt)

        def cleanup() -> None:
            ld.deleteLater()

        lt.started.connect(ld.run)
        ld.finished.connect(load_ui_relay.on_ok, Qt.ConnectionType.QueuedConnection)
        ld.failed.connect(load_ui_relay.on_fail, Qt.ConnectionType.QueuedConnection)
        ld.finished.connect(lt.quit)
        ld.failed.connect(lt.quit)
        lt.finished.connect(cleanup)

        load_thread = lt
        lt.start()

    def unload_model() -> None:
        nonlocal load_thread, hotkey_started
        controller.set_ready(False)
        stop_hotkey_listener()
        hotkey_started = False
        lt = load_thread
        if lt is not None and lt.isRunning():
            lt.requestInterruption()
            lt.wait(6000)
        engine.unload()
        tray.setToolTip("Buzz Mini — model unloaded (Models tab → Apply to load again)")
        main_win.models_panel().refresh_after_external_model_change()

    main_win.models_panel().model_apply_requested.connect(schedule_load)

    def on_settings_saved() -> None:
        refresh_ptt_chord_from_settings()
        controller.refresh_input_device()
        if controller.is_ready():
            attach_hotkey_listener()
            update_tooltip_ready()

    main_win.settings_panel().settings_saved.connect(on_settings_saved)

    open_action.triggered.connect(lambda: _show_main(None))
    models_action.triggered.connect(lambda: _show_main(MainTab.MODELS))
    settings_action.triggered.connect(lambda: _show_main(MainTab.SETTINGS))
    logs_action.triggered.connect(lambda: _show_main(MainTab.LOGS))
    donate_action.triggered.connect(lambda: _show_main(MainTab.DONATE))
    unload_action.triggered.connect(unload_model)

    def request_quit() -> None:
        main_win._force_quit = True
        app.quit()

    quit_action.triggered.connect(request_quit)

    def graceful_shutdown() -> None:
        nonlocal hotkey_listener, load_thread
        logger.info("Exiting: stopping listener, capture, downloads, load worker…")
        main_win.prepare_shutdown()
        stop_hotkey_listener()
        controller.shutdown()
        overlay.hide_overlay()
        lt = load_thread
        if lt is not None and lt.isRunning():
            lt.requestInterruption()
            if not lt.wait(8000):
                logger.warning("Load thread did not finish in time")
        engine.unload()

    app.aboutToQuit.connect(graceful_shutdown)

    # --- Wiring (before schedule_load so a fast cached load cannot emit PTT before slots exist)
    bridge.ptt_down.connect(controller.on_ptt_down)
    bridge.ptt_up.connect(controller.on_ptt_up)

    controller.overlay_listening.connect(overlay.show_listening)
    controller.overlay_transcribing.connect(overlay.show_transcribing)
    controller.overlay_hide.connect(overlay.hide_overlay)

    def on_text(text: str) -> None:
        t = (text or "").strip()
        logger.info("Transcription done (%d non-space chars)", len(t))
        if not t:
            overlay.hide_overlay()
            tray.showMessage(
                "Buzz Mini",
                "Recognition returned empty text. Try another microphone in Settings, "
                "or set BUZZMINI_LANGUAGE (e.g. ru). Text would not be pasted.",
                QSystemTrayIcon.MessageIcon.Information,
                6000,
            )
            return
        # Paste before hiding overlay (same order as Handy) so focus/clipboard settle correctly.
        _paste_via_clipboard(app, t)
        overlay.hide_overlay()

    def on_err(msg: str) -> None:
        overlay.hide_overlay()
        tray.showMessage("Buzz Mini", msg, QSystemTrayIcon.MessageIcon.Warning)

    controller.transcribe_done.connect(on_text, Qt.ConnectionType.QueuedConnection)
    controller.transcribe_failed.connect(on_err, Qt.ConnectionType.QueuedConnection)

    schedule_load()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
