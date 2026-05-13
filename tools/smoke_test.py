"""Quick import/shutdown smoke test (no tray, no model load)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


def main() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    from buzz_mini.engine import WhisperEngine, _resolve_download_root
    from buzz_mini.models_catalog import find_local_snapshot
    from buzz_mini.models_dialog import ModelsDialog
    from buzz_mini.ptt_chord import parse_ptt_chord_raw
    from buzz_mini.settings_store import DictateSettings

    root = _resolve_download_root()
    print("download_root:", root)
    print("tiny cached:", find_local_snapshot("tiny", root) is not None)

    e = WhisperEngine("tiny")
    e.unload()

    dlg = ModelsDialog(DictateSettings(), root)
    dlg.cancel_download_on_exit()

    assert DictateSettings.DEFAULT_PTT_CHORD == "ctrl_l+space"
    assert parse_ptt_chord_raw("ctrl_l+space")[2] == "Left Ctrl + Space"
    assert parse_ptt_chord_raw("ctrl+space")[2] == "Left Ctrl + Space"
    for cid in DictateSettings.PTT_CHORD_CHOICES:
        a, b, lab = parse_ptt_chord_raw(cid)
        assert a is not None and b is not None and lab

    print("SMOKE_OK")


if __name__ == "__main__":
    main()
