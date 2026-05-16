# -*- mode: python ; coding: utf-8 -*-
"""Windows onedir bundle (no console). From repo root:

  .\\.venv\\Scripts\\python.exe -m pip install -e \".[win-build]\"
  .\\.venv\\Scripts\\python.exe -m PyInstaller --noconfirm BuzzMini.spec
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

try:
    ROOT = Path(SPECPATH)
except NameError:  # very old PyInstaller: directory of the spec file
    ROOT = Path(SPEC).resolve().parent

_datas = []
_binaries = []
_hiddenimports: list[str] = []

for name in ("torch", "PyQt6", "ctranslate2", "onnxruntime", "av", "tokenizers"):
    try:
        ds, bs, hi = collect_all(name)
        _datas += ds
        _binaries += bs
        _hiddenimports += hi
    except Exception:
        pass

_datas += [(str(ROOT / "assets"), "assets")]

_hiddenimports += [
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
    "sounddevice",
]
_hiddenimports += collect_submodules("faster_whisper")
_hiddenimports += collect_submodules("pynput")

# Windows executable icon: assets/app.ico (multi-resolution .ico).
_app_ico = ROOT / "assets" / "app.ico"
_exe_icon = str(_app_ico) if _app_ico.is_file() and _app_ico.stat().st_size > 100 else None

a = Analysis(
    [str(ROOT / "buzz_mini" / "app.py")],
    pathex=[str(ROOT)],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BuzzMini",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_exe_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BuzzMini",
)
