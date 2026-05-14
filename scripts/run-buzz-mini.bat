@echo off
REM One-shot: ensure .venv, CUDA PyTorch (cu126) on Windows, editable install, then start BuzzMini.
setlocal
cd /d "%~dp0\.."
set "PY=%cd%\.venv\Scripts\python.exe"

where python >nul 2>&1
if errorlevel 1 (
    echo [BuzzMini] Python not found in PATH. Install Python 3.12+ and try again.
    pause
    exit /b 1
)

if not exist "%PY%" (
    echo [BuzzMini] Creating .venv...
    python -m venv .venv
    if errorlevel 1 (
        echo [BuzzMini] venv creation failed.
        pause
        exit /b 1
    )
)

echo [BuzzMini] Upgrading pip...
"%PY%" -m pip install -U pip -q
if errorlevel 1 (
    echo [BuzzMini] pip upgrade failed.
    pause
    exit /b 1
)

echo [BuzzMini] Checking PyTorch CUDA ^(cu126^)...
"%PY%" -c "import torch,sys; v=getattr(torch.version,'cuda',None); sys.exit(0 if v else 1)" 2>nul
if errorlevel 1 (
    echo [BuzzMini] Installing PyTorch with CUDA from pytorch.org ^(may take a few minutes^)...
    "%PY%" -m pip install torch --index-url https://download.pytorch.org/whl/cu126
    if errorlevel 1 (
        echo [BuzzMini] PyTorch install failed.
        pause
        exit /b 1
    )
)

echo [BuzzMini] Installing / updating package ^(editable^)...
"%PY%" -m pip install -e . -q
if errorlevel 1 (
    echo [BuzzMini] pip install -e . failed.
    pause
    exit /b 1
)

echo [BuzzMini] Starting app...
"%PY%" -m buzz_mini.app %*
if errorlevel 1 pause
