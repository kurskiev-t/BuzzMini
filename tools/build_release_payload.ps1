# Pack dist\BuzzMini into a .7z for GitHub Releases (downloaded by BuzzMini-Setup at install time).
param(
    [switch]$Clean,
    [string]$ProductVersion = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

$BundleDir = Join-Path $RepoRoot "dist\BuzzMini"
$ExeOut = Join-Path $BundleDir "BuzzMini.exe"

if (-not (Test-Path $ExeOut)) {
    Write-Host "[BuzzMini] dist\BuzzMini missing — running tools\build_windows.ps1..."
    & (Join-Path $RepoRoot "tools\build_windows.ps1")
}
if (-not (Test-Path $ExeOut)) {
    Write-Error "Missing $ExeOut — run tools\build_windows.ps1 first."
}

if (-not $ProductVersion) {
    $ProductVersion = "1.0.0"
    $pp = Join-Path $RepoRoot "pyproject.toml"
    if (Test-Path $pp) {
        $txt = Get-Content $pp -Raw
        if ($txt -match 'version\s*=\s*"([^"]+)"') { $ProductVersion = $matches[1] }
    }
}

$releaseCfg = Join-Path $RepoRoot "installer\release.json"
$repo = "kurskiev-t/BuzzMini"
$tagTemplate = "v{version}"
$assetTemplate = "BuzzMini-{version}-win64.7z"
if (Test-Path $releaseCfg) {
    $cfg = Get-Content $releaseCfg -Raw | ConvertFrom-Json
    if ($cfg.repository) { $repo = $cfg.repository }
    if ($cfg.tagTemplate) { $tagTemplate = $cfg.tagTemplate }
    if ($cfg.assetTemplate) { $assetTemplate = $cfg.assetTemplate }
}

$assetName = $assetTemplate.Replace("{version}", $ProductVersion)
$tag = $tagTemplate.Replace("{version}", $ProductVersion)
$outArchive = Join-Path $RepoRoot "dist\$assetName"

$sevenZ = $null
foreach ($c in @(
        "${Env:ProgramFiles}\7-Zip\7z.exe",
        "${Env:ProgramFiles(x86)}\7-Zip\7z.exe"
    )) {
    if (Test-Path $c) { $sevenZ = $c; break }
}
if (-not $sevenZ) {
    Write-Error "7-Zip not found. Install from https://www.7-zip.org/ (need 7z.exe to create the release archive; 7zr.exe is extract-only)."
}

if ($Clean -and (Test-Path $outArchive)) {
    Remove-Item -Force $outArchive
}

Write-Host "[BuzzMini] Creating release payload (may take several minutes)..."
Write-Host "  Source:  $BundleDir"
Write-Host "  Output:  $outArchive"

if (Test-Path $outArchive) { Remove-Item -Force $outArchive }

Push-Location $BundleDir
try {
    # Archive root = BuzzMini.exe + _internal (installer extracts directly into $INSTDIR)
    & $sevenZ a -t7z -mx=5 -mmt=on $outArchive * | Write-Host
    if ($LASTEXITCODE -ne 0) { throw "7-Zip failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

if (-not (Test-Path $outArchive)) {
    Write-Error "Archive not created: $outArchive"
}

$sizeGb = [math]::Round((Get-Item $outArchive).Length / 1GB, 2)
$payloadUrl = "https://github.com/$repo/releases/download/$tag/$assetName"

Write-Host ""
Write-Host "[BuzzMini] OK: $outArchive ($sizeGb GB compressed)"
Write-Host ""
Write-Host "Upload to GitHub Release:"
Write-Host "  Repository: https://github.com/$repo"
Write-Host "  Tag:        $tag"
Write-Host "  Asset file: $assetName"
Write-Host "  Direct URL: $payloadUrl"
Write-Host ""
Write-Host "Then build and upload Setup.exe:  .\tools\build_installer.ps1"
