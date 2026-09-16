from __future__ import annotations

import subprocess
import sys


def win32_video_adapter_names() -> list[str]:
    if sys.platform != "win32":
        return []
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            creationflags=creationflags,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def adapter_blob(names: list[str]) -> str:
    return " ".join(names).lower()


def has_nvidia_adapter(names: list[str]) -> bool:
    blob = adapter_blob(names)
    return any(tok in blob for tok in ("nvidia", "geforce", "quadro", "rtx ", "gtx"))


def has_amd_adapter(names: list[str]) -> bool:
    blob = adapter_blob(names)
    return any(tok in blob for tok in ("amd", "radeon", "rx "))
