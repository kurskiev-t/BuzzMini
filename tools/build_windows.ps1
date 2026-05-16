# Build Windows onedir: dist/BuzzMini/BuzzMini.exe
# Requires .venv with project + CUDA torch (same as run-buzz-mini flow).
param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$Py = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Write-Error "Expected $Py - create .venv and install the project first (see README)."
}

if ($Clean) {
    Remove-Item -Recurse -Force (Join-Path $RepoRoot "build") -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force (Join-Path $RepoRoot "dist\BuzzMini") -ErrorAction SilentlyContinue
}

# Single-quoted: avoids PowerShell treating [BuzzMini] as a type / expression inside "... "
Write-Host '[BuzzMini] Installing PyInstaller extra (win-build)...'
# $RepoRoot[win-build] inside "..." is parsed as index access - use concatenation:
& $Py -m pip install -q -e ($RepoRoot + '[win-build]')

Write-Host '[BuzzMini] Running PyInstaller (onedir, can take several minutes, large output)...'
& $Py -m PyInstaller --noconfirm (Join-Path $RepoRoot "BuzzMini.spec")

$Out = Join-Path $RepoRoot "dist\BuzzMini\BuzzMini.exe"
if (Test-Path $Out) {
    Write-Host ('[BuzzMini] OK: ' + $Out)
} else {
    Write-Error "Expected output missing: $Out"
}
