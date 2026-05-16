# Fetch 7zr.exe for the NSIS installer (redistributable console 7-Zip).
$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$destDir = Join-Path $RepoRoot "installer\redist"
$dest = Join-Path $destDir "7zr.exe"

if (Test-Path $dest) {
    return $dest
}

New-Item -ItemType Directory -Force -Path $destDir | Out-Null
$uri = "https://www.7-zip.org/a/7zr.exe"
Write-Host "[BuzzMini] Downloading 7zr.exe -> $dest"
Invoke-WebRequest -Uri $uri -OutFile $dest -UseBasicParsing

if (-not (Test-Path $dest)) {
    Write-Error "Failed to download 7zr.exe from $uri"
}
return $dest
