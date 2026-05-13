"""Push-to-talk chord: parse stored/env string into pynput keys + display label."""

from __future__ import annotations

import logging
import os
import sys

from buzz_mini.settings_store import DictateSettings

logger = logging.getLogger(__name__)

_CTRL_L_ALIASES = frozenset({"ctrl_l", "lctrl", "left_ctrl", "control_l"})
_CTRL_R_ALIASES = frozenset({"ctrl_r", "rctrl", "right_ctrl", "control_r"})
# Handy-style default on Windows/Linux is "ctrl+space" (no left/right) — treat as left Ctrl.
_CTRL_GENERIC_ALIASES = frozenset({"ctrl", "control"})
_WIN_ALIASES = frozenset({"win", "windows", "cmd", "meta", "lwin", "rwin", "super"})


def effective_ptt_chord_raw(settings: DictateSettings) -> str:
    """Non-empty BUZZMINI_PTT_CHORD overrides QSettings."""
    env = os.environ.get("BUZZMINI_PTT_CHORD", "").strip()
    if env:
        return env.lower().replace(" ", "")
    return settings.ptt_chord_id()


def parse_ptt_chord_raw(raw: str) -> tuple[object, object, str]:
    """Return (modifier_key, partner_key, human label). Two keys must be held (chord)."""
    from pynput import keyboard

    s = raw.strip().lower().replace(" ", "")
    if not s:
        s = DictateSettings.DEFAULT_PTT_CHORD
    if "+" not in s:
        logger.warning("PTT chord %r has no '+'; using %s", raw, DictateSettings.DEFAULT_PTT_CHORD)
        s = DictateSettings.DEFAULT_PTT_CHORD
    left, _, right = s.partition("+")
    left = left.strip()
    right = right.strip()

    if left in _CTRL_R_ALIASES:
        mod_key = keyboard.Key.ctrl_r
        mod_side = "Right"
    elif left in _CTRL_GENERIC_ALIASES:
        mod_key = keyboard.Key.ctrl_l
        mod_side = "Left"
    elif left in _CTRL_L_ALIASES or not left:
        mod_key = keyboard.Key.ctrl_l
        mod_side = "Left"
    else:
        logger.warning("PTT chord modifier %r unknown; using left ctrl", left)
        mod_key = keyboard.Key.ctrl_l
        mod_side = "Left"

    if right in ("space", "spc", ""):
        partner_key = keyboard.Key.space
        partner_word = "Space"
    elif right in _WIN_ALIASES:
        partner_key = keyboard.Key.cmd
        if sys.platform == "darwin":
            partner_word = "Cmd"
        elif sys.platform == "win32":
            partner_word = "Win"
        else:
            partner_word = "Super"
    else:
        logger.warning("PTT chord partner %r unknown; using space", right)
        partner_key = keyboard.Key.space
        partner_word = "Space"

    label = f"{mod_side} Ctrl + {partner_word}"
    return mod_key, partner_key, label
