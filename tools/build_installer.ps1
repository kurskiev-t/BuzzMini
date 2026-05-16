# Build small NSIS setup.exe (downloads PyInstaller bundle from GitHub Releases at install time).
# Prerequisite: NSIS 3+ (makensis.exe). Does NOT require dist\BuzzMini.
param(
    [string]$ProductVersion = "",
    [string]$PayloadUrl = "",
    [string]$GithubRepo = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

& (Join-Path $RepoRoot "tools\ensure_7zr.ps1") | Out-Null

$makensis = $null
$cmd = Get-Command makensis -ErrorAction SilentlyContinue
if ($cmd) { $makensis = $cmd.Source }
if (-not $makensis) {
    foreach ($c in @(
            "${Env:ProgramFiles(x86)}\NSIS\makensis.exe",
            "$Env:ProgramFiles\NSIS\makensis.exe"
        )) {
        if (Test-Path $c) { $makensis = $c; break }
    }
}
if (-not $makensis) {
    Write-Error "makensis.exe not found. Install NSIS (winget install NSIS.NSIS) and re-run."
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
if ($GithubRepo) { $repo = $GithubRepo }

$tag = $tagTemplate.Replace("{version}", $ProductVersion)
$asset = $assetTemplate.Replace("{version}", $ProductVersion)
if (-not $PayloadUrl) {
    $PayloadUrl = "https://github.com/$repo/releases/download/$tag/$asset"
}

$outFile = Join-Path $RepoRoot "dist\BuzzMini-Setup-$ProductVersion.exe"
$nsi = Join-Path $RepoRoot "installer\BuzzMini.nsi"
$null = New-Item -ItemType Directory -Force -Path (Split-Path $outFile)

Write-Host "[BuzzMini] NSIS web-installer compile"
Write-Host "  makensis:     $makensis"
Write-Host "  OUTFILE:      $outFile"
Write-Host "  PAYLOAD_URL:  $PayloadUrl"

$makensisArgs = @(
    "/V2",
    "/DOUTFILE=$outFile",
    "/DPRODUCT_VERSION=$ProductVersion",
    "/DPAYLOAD_URL=$PayloadUrl",
    "/DGITHUB_REPO=$repo",
    $nsi
)
& $makensis @makensisArgs

if (-not (Test-Path $outFile)) {
    Write-Error "Expected installer missing: $outFile"
}

$sizeMb = [math]::Round((Get-Item $outFile).Length / 1MB, 2)
Write-Host "[BuzzMini] OK: $outFile ($sizeMb MB)"
Write-Host ""
Write-Host "Upload this Setup.exe to the same GitHub Release as the payload .7z."
Write-Host "Payload URL baked into installer:"
Write-Host "  $PayloadUrl"
