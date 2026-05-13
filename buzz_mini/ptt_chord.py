"""Push-to-talk chord: parse stored/env string into pynput keys + display label."""

from __future__ import annotations

import logging
import os

from buzz_mini.settings_store import DictateSettings

logger = logging.getLogger(__name__)


def effective_ptt_chord_raw(settings: DictateSettings) -> str:
    """Non-empty BUZZMINI_PTT_CHORD overrides QSettings."""
    env = os.environ.get("BUZZMINI_PTT_CHORD", "").strip()
    if env:
        return env.lower().replace(" ", "")
    return settings.ptt_chord_id()


def parse_ptt_chord_raw(raw: str) -> tuple[object, object, str]:
    """Return (ctrl_r_key, partner_key, human label). Unknown partner → space."""
    from pynput import keyboard

    s = raw.strip().lower().replace(" ", "")
    if not s:
        s = "ctrl_r+space"
    if "+" not in s:
        logger.warning("PTT chord %r has no '+'; using ctrl_r+space", raw)
        s = "ctrl_r+space"
    left, _, right = s.partition("+")
    left = left.strip()
    right = right.strip()

    ctrl_aliases = {"ctrl_r", "rctrl", "right_ctrl"}
    if left not in ctrl_aliases:
        logger.warning("PTT chord left key %r is not right ctrl; using ctrl_r anyway", left)

    ctrl_key = keyboard.Key.ctrl_r

    win_like = {"win", "windows", "cmd", "meta", "lwin", "rwin", "super"}
    if right in ("space", "spc"):
        return ctrl_key, keyboard.Key.space, "Right Ctrl + Space"
    if right in win_like:
        return ctrl_key, keyboard.Key.cmd, "Right Ctrl + Win"

    logger.warning("PTT chord partner %r unknown; using space", right)
    return ctrl_key, keyboard.Key.space, "Right Ctrl + Space"
