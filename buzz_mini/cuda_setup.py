"""
CUDA DLL / shared-library bootstrap (adapted from Buzz `buzz/cuda_setup.py`).
Import this module before torch or faster-whisper.
"""

import ctypes
import os
import platform
import sys
from pathlib import Path

def _get_nvidia_package_lib_dirs() -> list[Path]:
    lib_dirs: list[Path] = []
    site_packages_dirs: list[Path] = []
    for path in sys.path:
        if "site-packages" in path:
            site_packages_dirs.append(Path(path))

    if getattr(sys, "frozen", False):
        frozen_lib_dir = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path(sys.executable).parent
        nvidia_dir = frozen_lib_dir / "nvidia"
        if nvidia_dir.exists():
            for pkg_dir in nvidia_dir.iterdir():
                if pkg_dir.is_dir():
                    for sub in ("lib", "bin"):
                        p = pkg_dir / sub
                        if p.exists():
                            lib_dirs.append(p)

    for sp_dir in site_packages_dirs:
        nvidia_dir = sp_dir / "nvidia"
        if nvidia_dir.exists():
            for pkg_dir in nvidia_dir.iterdir():
                if pkg_dir.is_dir():
                    for sub in ("lib", "bin"):
                        p = pkg_dir / sub
                        if p.exists():
                            lib_dirs.append(p)

    return lib_dirs


def _setup_windows_dll_directories() -> None:
    lib_dirs = _get_nvidia_package_lib_dirs()
    for lib_dir in lib_dirs:
        try:
            os.add_dll_directory(str(lib_dir))
        except (OSError, AttributeError):
            pass


def _preload_linux_libraries() -> None:
    lib_dirs = _get_nvidia_package_lib_dirs()
    skip_patterns = ["libnvblas"]
    loaded_libs: set[str] = set()

    for lib_dir in lib_dirs:
        if not lib_dir.exists():
            continue
        for lib_file in sorted(lib_dir.glob("*.so*")):
            if lib_file.name in loaded_libs:
                continue
            if lib_file.is_symlink() and not lib_file.exists():
                continue
            if any(pattern in lib_file.name for pattern in skip_patterns):
                continue
            try:
                ctypes.CDLL(str(lib_file), mode=ctypes.RTLD_GLOBAL)
                loaded_libs.add(lib_file.name)
            except OSError:
                pass


def setup_cuda_libraries() -> None:
    system = platform.system()
    if system == "Windows":
        _setup_windows_dll_directories()
    elif system == "Linux":
        _preload_linux_libraries()


setup_cuda_libraries()
