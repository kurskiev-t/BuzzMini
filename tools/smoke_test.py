"""Quick import/shutdown smoke test (no tray, no model load)."""

from __future__ import annotations

import os
import sys


def main() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    from buzz_mini.engine import WhisperEngine, _resolve_download_root
    from buzz_mini.models_catalog import find_local_snapshot
    from buzz_mini.models_dialog import ModelsDialog
    from buzz_mini.settings_store import DictateSettings

    root = _resolve_download_root()
    print("download_root:", root)
    print("tiny cached:", find_local_snapshot("tiny", root) is not None)

    e = WhisperEngine("tiny")
    e.unload()

    dlg = ModelsDialog(DictateSettings(), root)
    dlg.cancel_download_on_exit()

    print("SMOKE_OK")


if __name__ == "__main__":
    main()
