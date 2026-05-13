@echo off
REM Запуск из .venv репозитория (корень — родитель этой папки). Нужен после uv sync / pip install.
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" (
    echo [BuzzMini] Нет .venv\Scripts\python.exe в "%cd%"
    echo Установите зависимости: uv sync   см. README
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m buzz_mini.app %*
if errorlevel 1 pause
