# Pack faster-whisper snapshots from the local HF cache into GitHub Release assets.
# Produces dist\model-assets\buzzmini-model-<id>.zip + models.json (manifest with sha256).
# Run on the machine where models are already downloaded (notebook):
#
#   .\tools\make_model_assets.ps1
#   .\tools\make_model_assets.ps1 -ModelIds @("tiny", "tiny.en", "base.en")
#
# Then upload the zips + models.json to a GitHub Release with tag "models-v1".
# Asset names must match github_asset_name() in buzz_mini/models_catalog.py:
#   buzzmini-model-<id>.zip  (dots in id stay, e.g. buzzmini-model-tiny.en.zip)
param(
    [string[]]$ModelIds = @(
        "tiny", "tiny.en",
        "base", "base.en",
        "small", "small.en",
        "medium", "medium.en",
        "large-v1", "large-v2", "large-v3", "large-v3-turbo"
    ),
    [string]$CacheRoot = "",
    [string]$ModelsTag = "models-v1",
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $CacheRoot) {
    $CacheRoot = Join-Path $env:LOCALAPPDATA "BuzzMini\BuzzMini\Cache\models"
}
if (-not $OutDir) {
    $OutDir = Join-Path $RepoRoot "dist\model-assets"
}
$null = New-Item -ItemType Directory -Force -Path $OutDir

# Same allow-list as buzz_mini/models_catalog.py ALLOW_PATTERNS.
$AllowFiles = @("model.bin", "pytorch_model.bin", "config.json", "preprocessor_config.json", "tokenizer.json")
$AllowWildcards = @("vocabulary.*")

function Find-SnapshotDir([string]$ModelId) {
    # HF cache dirs: models--Systran--faster-whisper-<id> (dots kept), turbo lives under mobiuslabsgmbh.
    $cands = Get-ChildItem -Directory -Path $CacheRoot -Filter "models--*--faster-whisper-*" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*-faster-whisper-$ModelId" }
    foreach ($c in $cands) {
        $snaps = Join-Path $c.FullName "snapshots"
        if (-not (Test-Path $snaps)) { continue }
        $best = Get-ChildItem -Directory -Path $snaps -ErrorAction SilentlyContinue |
            Where-Object { Test-Path (Join-Path $_.FullName "model.bin") } |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($best) { return $best.FullName }
    }
    return $null
}

$assets = @{}
$hashes = @{}
$sizes = @{}

foreach ($id in $ModelIds) {
    $snap = Find-SnapshotDir $id
    if (-not $snap) {
        Write-Warning "[BuzzMini] snapshot for '$id' not found in $CacheRoot - skipped (download it first via Models tab)."
        continue
    }
    $stage = Join-Path ([System.IO.Path]::GetTempPath()) ("buzzmini-model-" + $id)
    if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
    $null = New-Item -ItemType Directory -Force -Path $stage

    $files = Get-ChildItem -File -Path $snap | Where-Object {
        $n = $_.Name
        ($AllowFiles -contains $n) -or (@($AllowWildcards | Where-Object { $n -like $_ }).Count -gt 0)
    }
    if (-not ($files | Where-Object { $_.Name -eq "model.bin" })) {
        Write-Warning "[BuzzMini] no model.bin in $snap - skipped."
        continue
    }
    foreach ($f in $files) { Copy-Item $f.FullName (Join-Path $stage $f.Name) }

    $zipName = "buzzmini-model-$id.zip"
    $zipPath = Join-Path $OutDir $zipName
    if (Test-Path $zipPath) { Remove-Item -Force $zipPath }
    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -CompressionLevel Optimal
    $h = (Get-FileHash -Algorithm SHA256 $zipPath).Hash.ToLowerInvariant()
    $sz = (Get-Item $zipPath).Length

    $assets[$id] = $zipName
    $hashes[$id] = $h
    $sizes[$id] = $sz
    Write-Host ("[BuzzMini] OK: {0} ({1:N1} MB) sha256={2}" -f $zipName, ($sz / 1MB), $h)
    Remove-Item -Recurse -Force $stage
}

if ($assets.Count -eq 0) { Write-Error "No model assets produced - check -CacheRoot / -ModelIds." }

$manifest = [ordered]@{
    tag    = $ModelsTag
    repo   = "kurskiev-t/BuzzMini"
    assets = $assets
    sha256 = $hashes
    sizes  = $sizes
}
$manifestPath = Join-Path $OutDir "models.json"
# NB: Set-Content -Encoding UTF8 на Windows PowerShell 5.1 пишет BOM, а клиентский
# json.loads (и GitHub-зеркало) ждёт чистый UTF-8 — пишем явно без BOM.
[System.IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 4), (New-Object System.Text.UTF8Encoding $false))
Write-Host "[BuzzMini] manifest: $manifestPath"
Write-Host ""
Write-Host "Upload to GitHub Release:"
Write-Host "  Tag:  $ModelsTag  (create new release with this tag)"
Write-Host "  Files: all buzzmini-model-*.zip from $OutDir + models.json"
