"""Headless smoke test: QApplication + BuzzMainWindow, no tray / PTT / model load."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    from buzz_mini.main_window import BuzzMainWindow
    from buzz_mini.settings_store import DictateSettings

    app = QApplication(sys.argv)
    tmp = Path(tempfile.mkdtemp(prefix="buzzmini-ci-"))
    models_dir = tmp / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    settings = DictateSettings()
    w = BuzzMainWindow(settings, str(models_dir))
    w.show()
    app.processEvents()
    w.prepare_shutdown()
    w.close()
    app.processEvents()
    print("ci_smoke_ok", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
