"""Paths to bundled resources (dev tree vs PyInstaller)."""

from __future__ import annotations

import sys
from pathlib import Path


def bundle_root() -> Path:
    """Dev: repository root (parent of ``buzz_mini``). Frozen: PyInstaller ``_MEIPASS``."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def assets_dir() -> Path:
    return bundle_root() / "assets"
