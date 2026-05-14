"""Single main window: tabs for Models, Settings, Logs, Donate."""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import TYPE_CHECKING, Optional

from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import QApplication, QMainWindow, QMenuBar, QTabWidget, QWidget

from buzz_mini.donate_dialog import DonatePanel
from buzz_mini.log_panel import LogPanel, QtLogHandler
from buzz_mini.models_dialog import ModelsPanel
from buzz_mini.settings_dialog import SettingsPanel

if TYPE_CHECKING:
    from buzz_mini.settings_store import DictateSettings


class MainTab(IntEnum):
    MODELS = 0
    SETTINGS = 1
    LOGS = 2
    DONATE = 3


class BuzzMainWindow(QMainWindow):
    def __init__(
        self,
        settings: "DictateSettings",
        download_root: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Buzz Mini")
        self.setMinimumSize(520, 420)
        self._settings = settings

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._models = ModelsPanel(settings, download_root, self)
        self._settings_panel = SettingsPanel(settings, self)
        self._logs = LogPanel(self)
        self._donate = DonatePanel(self)

        self._tabs.addTab(self._models, "Models")
        self._tabs.addTab(self._settings_panel, "Settings")
        self._tabs.addTab(self._logs, "Logs")
        self._tabs.addTab(self._donate, "Donate")

        self.setCentralWidget(self._tabs)

        mb = QMenuBar(self)
        view = mb.addMenu("&View")
        act_logs = QAction("&Logs", self)
        act_logs.triggered.connect(lambda: self.show_tab(MainTab.LOGS))
        view.addAction(act_logs)
        self.setMenuBar(mb)

        self._qt_log_handler: Optional[QtLogHandler] = None
        self._force_quit = False
        self._install_log_handler()

    def prepare_shutdown(self) -> None:
        """Allow window to close and detach logging before process exit."""
        self._force_quit = True
        self.remove_log_handler()
        self.cancel_downloads_on_exit()

    def models_panel(self) -> ModelsPanel:
        return self._models

    def settings_panel(self) -> SettingsPanel:
        return self._settings_panel

    def log_panel(self) -> LogPanel:
        return self._logs

    def _install_log_handler(self) -> None:
        fmt = logging.Formatter("%(levelname)s %(name)s: %(message)s")
        h = QtLogHandler(self._logs.emitter())
        h.setLevel(logging.DEBUG)
        h.setFormatter(fmt)
        logging.getLogger().addHandler(h)
        self._qt_log_handler = h

    def remove_log_handler(self) -> None:
        if self._qt_log_handler is not None:
            logging.getLogger().removeHandler(self._qt_log_handler)
            self._qt_log_handler = None

    def show_tab(self, tab: MainTab | int) -> None:
        self._tabs.setCurrentIndex(int(tab))
        self.show()
        self.raise_()
        self.activateWindow()

    def current_main_tab(self) -> int:
        return self._tabs.currentIndex()

    def cancel_downloads_on_exit(self) -> None:
        self._models.cancel_download_on_exit()

    def close_to_tray(self) -> bool:
        return self._settings.close_to_tray_on_window_close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._force_quit:
            event.accept()
            return
        if self.close_to_tray():
            event.ignore()
            self.hide()
            return
        self._force_quit = True
        inst = QApplication.instance()
        if inst is not None:
            inst.quit()
        event.ignore()
