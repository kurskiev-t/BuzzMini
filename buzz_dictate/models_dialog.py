"""Model picker + download / delete / open folder — Buzz Models tab (Faster Whisper only)."""

from __future__ import annotations

import os
from typing import Iterator, Optional

from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from buzz_dictate.download_progress import ModelDownloadProgressDialog
from buzz_dictate.model_download import ModelSnapshotDownloadTask
from buzz_dictate.models_catalog import (
    MODEL_ENTRIES,
    delete_model_cache,
    find_local_snapshot,
    open_snapshot_in_explorer,
    repo_id_for_model,
    title_for_id,
)
from buzz_dictate.settings_store import DictateSettings


class ModelsDialog(QDialog):
    def __init__(
        self,
        settings: DictateSettings,
        download_root: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Models — Buzz Dictate")
        self._settings = settings
        self._download_root = download_root
        self._selected_id = settings.selected_model_id()
        self._pool = QThreadPool()
        self._pool.setMaxThreadCount(1)
        self._current_task: Optional[ModelSnapshotDownloadTask] = None
        self._progress: Optional[ModelDownloadProgressDialog] = None

        info = QLabel(
            "Faster Whisper models are stored next to Buzz when possible.\n"
            f"Cache: {download_root}"
        )
        info.setWordWrap(True)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(1)
        self._tree.setHeaderHidden(True)
        self._tree.setAlternatingRowColors(True)
        self._tree.currentItemChanged.connect(self._on_current_changed)

        dl_row = QHBoxLayout()
        self._download_btn = QPushButton("Download")
        self._download_btn.clicked.connect(self._on_download)
        self._location_btn = QPushButton("Show file location")
        self._location_btn.clicked.connect(self._on_show_location)
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._on_delete)
        dl_row.addWidget(self._download_btn)
        dl_row.addWidget(self._location_btn)
        dl_row.addStretch(1)
        dl_row.addWidget(self._delete_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(info)
        layout.addWidget(self._tree)
        layout.addLayout(dl_row)
        layout.addWidget(buttons)

        self._populate_tree()
        self._sync_buttons()

    def cancel_download_on_exit(self) -> None:
        """Stop HF download and close progress UI (app shutdown or dialog closed)."""
        self._on_download_cancel()
        if self._progress is not None:
            self._progress.close()
            self._progress = None

    def closeEvent(self, event: QCloseEvent) -> None:
        self.cancel_download_on_exit()
        super().closeEvent(event)

    def _populate_tree(self) -> None:
        self._tree.clear()
        downloaded_root = QTreeWidgetItem(self._tree)
        downloaded_root.setText(0, "Downloaded")
        downloaded_root.setFlags(downloaded_root.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        available_root = QTreeWidgetItem(self._tree)
        available_root.setText(0, "Available for Download")
        available_root.setFlags(available_root.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        for entry in MODEL_ENTRIES:
            installed = find_local_snapshot(entry.model_id, self._download_root) is not None
            parent = downloaded_root if installed else available_root
            item = QTreeWidgetItem(parent)
            item.setText(0, entry.title)
            item.setData(0, Qt.ItemDataRole.UserRole, entry.model_id)

        self._tree.expandToDepth(2)

        # Select current model
        self._select_model_id(self._selected_id)

    def _iter_items(self, root: QTreeWidgetItem) -> Iterator[QTreeWidgetItem]:
        yield root
        for i in range(root.childCount()):
            yield from self._iter_items(root.child(i))

    def _all_items(self) -> Iterator[QTreeWidgetItem]:
        for ti in range(self._tree.topLevelItemCount()):
            yield from self._iter_items(self._tree.topLevelItem(ti))

    def _select_model_id(self, model_id: str) -> None:
        for item in self._all_items():
            mid = item.data(0, Qt.ItemDataRole.UserRole)
            if mid == model_id:
                self._tree.setCurrentItem(item)
                return

    def _current_model_id(self) -> Optional[str]:
        cur = self._tree.currentItem()
        if cur is None:
            return None
        mid = cur.data(0, Qt.ItemDataRole.UserRole)
        return str(mid) if mid else None

    def _on_current_changed(self, _cur: QTreeWidgetItem, _prev: QTreeWidgetItem) -> None:
        mid = self._current_model_id()
        if mid:
            self._selected_id = mid
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        mid = self._current_model_id()
        if not mid:
            self._download_btn.setEnabled(False)
            self._location_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)
            return
        installed = find_local_snapshot(mid, self._download_root) is not None
        self._download_btn.setVisible(not installed)
        self._download_btn.setEnabled(True)
        self._location_btn.setVisible(installed)
        self._location_btn.setEnabled(installed)
        self._delete_btn.setVisible(installed)
        self._delete_btn.setEnabled(installed)

    def _on_download(self) -> None:
        mid = self._current_model_id()
        if not mid:
            return
        os.makedirs(self._download_root, exist_ok=True)

        self._progress = ModelDownloadProgressDialog(self)
        self._progress.canceled.connect(self._on_download_cancel)

        self._download_btn.setEnabled(False)

        task = ModelSnapshotDownloadTask(repo_id_for_model(mid), self._download_root)
        self._current_task = task
        task.signals.finished.connect(lambda _p: self._on_download_finished())
        task.signals.error.connect(self._on_download_error)
        self._pool.start(task)
        self._progress.show()

    def _on_download_cancel(self) -> None:
        if self._current_task:
            self._current_task.cancel()

    def _on_download_finished(self) -> None:
        if self._progress:
            self._progress.close()
            self._progress = None
        self._current_task = None
        self._download_btn.setEnabled(True)
        self._populate_tree()
        self._sync_buttons()

    def _on_download_error(self, msg: str) -> None:
        if self._progress:
            self._progress.close()
            self._progress = None
        self._current_task = None
        self._download_btn.setEnabled(True)
        QMessageBox.warning(self, "Buzz Dictate", f"Download failed:\n{msg}")
        self._populate_tree()
        self._sync_buttons()

    def _on_show_location(self) -> None:
        mid = self._current_model_id()
        if mid:
            open_snapshot_in_explorer(mid, self._download_root)

    def _on_delete(self) -> None:
        mid = self._current_model_id()
        if not mid:
            return
        title = title_for_id(mid)
        reply = QMessageBox.question(
            self,
            "Delete model",
            f"Remove “{title}” from the Hugging Face cache on disk?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        delete_model_cache(mid, self._download_root)
        self._populate_tree()
        self._sync_buttons()

    def _on_accept(self) -> None:
        mid = self._current_model_id()
        if not mid:
            QMessageBox.information(self, "Buzz Dictate", "Select a model.")
            return
        if find_local_snapshot(mid, self._download_root) is None:
            QMessageBox.information(
                self,
                "Buzz Dictate",
                f"“{title_for_id(mid)}” is not downloaded yet.\nUse Download first.",
            )
            return
        self._settings.set_selected_model_id(mid)
        self.accept()
