"""PortAudio input device list (sounddevice), same stack as Buzz live recording."""

from __future__ import annotations

import logging
from typing import Optional

import sounddevice as sd

logger = logging.getLogger(__name__)


def default_input_device_index() -> Optional[int]:
    try:
        i = sd.default.device[0]
        if i is None:
            return None
        i = int(i)
        return i if i >= 0 else None
    except Exception:
        logger.exception("Could not read default input device")
        return None


def input_devices_for_ui() -> list[tuple[Optional[int], str]]:
    """(device_index or None for system default, label)."""
    rows: list[tuple[Optional[int], str]] = [(None, "Default — system input")]
    try:
        default_in = default_input_device_index()
        devices = sd.query_devices()
    except Exception as e:
        logger.warning("sounddevice.query_devices failed: %s", e)
        return rows

    for i, d in enumerate(devices):
        if not isinstance(d, dict):
            continue
        if int(d.get("max_input_channels", 0) or 0) < 1:
            continue
        name = str(d.get("name", f"device {i}"))
        suffix = " (default)" if default_in is not None and i == default_in else ""
        rows.append((i, f"{i}: {name}{suffix}"))
    return rows
