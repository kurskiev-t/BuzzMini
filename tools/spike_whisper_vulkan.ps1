# Spike: build whisper.cpp (optional), download small ggml model, transcribe a test tone/wav.
param(
    [switch]$SkipBuild,
    [string]$ModelUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin",
    [string]$WavPath = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

if (-not $SkipBuild) {
    & (Join-Path $RepoRoot "tools\build_whispercpp_windows.ps1")
}

$cliCandidates = @(
    (Join-Path $RepoRoot "third_party\whisper.cpp\build\bin\Release\whisper-cli.exe"),
    (Join-Path $RepoRoot "third_party\whisper.cpp\build\bin\whisper-cli.exe")
)
$cli = $cliCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $cli) {
    Write-Error "whisper-cli.exe missing. Run without -SkipBuild or set BUZZMINI_WHISPER_CLI."
}

$modelsDir = Join-Path $RepoRoot "models"
New-Item -ItemType Directory -Force -Path $modelsDir | Out-Null
$ggml = Join-Path $modelsDir "ggml-base.bin"
if (-not (Test-Path $ggml)) {
    Write-Host "[spike] Downloading $ModelUrl -> $ggml"
    Invoke-WebRequest -Uri $ModelUrl -OutFile $ggml -UseBasicParsing
}

if (-not $WavPath) {
    $WavPath = Join-Path $env:TEMP "buzzmini-spike.wav"
    Write-Host "[spike] Generating 2s 440Hz test wav: $WavPath"
    & $RepoRoot\.venv\Scripts\python.exe -c @"
import wave, math, struct
sr=16000; dur=2.0; freq=440.0
with wave.open(r'$WavPath','wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    for i in range(int(sr*dur)):
        v=int(16000*math.sin(2*math.pi*freq*i/sr))
        w.writeframes(struct.pack('<h', v))
"@
}

Write-Host "[spike] Running whisper-cli (Vulkan build if GGML_VULKAN was on)..."
& $cli -m $ggml -f $WavPath -nt -ngl 99

Write-Host ""
Write-Host "[spike] App test:"
Write-Host "  `$env:BUZZMINI_BACKEND='vulkan'"
Write-Host "  `$env:BUZZMINI_WHISPER_CLI='$cli'"
Write-Host "  `$env:BUZZMINI_GGML_MODEL='$ggml'"
Write-Host "  .\.venv\Scripts\python.exe -m buzz_mini.app"
