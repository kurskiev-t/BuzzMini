# Build whisper.cpp with Vulkan (GGML_VULKAN) for BuzzMini amd backend / dev testing.
# Requires: git, cmake (PATH), Visual Studio with C++ workload, Vulkan SDK (core is enough).
param(
    [switch]$Clean,
    [string]$WhisperCppRef = "master"
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ThirdParty = Join-Path $RepoRoot "third_party"
$WhisperDir = Join-Path $ThirdParty "whisper.cpp"
$BuildDir = Join-Path $WhisperDir "build"

function Require-Command {
    param([string]$Name, [string]$InstallHint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Error "$Name not found on PATH. $InstallHint"
    }
}

function Get-VsInstallPath {
    $vswhere = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
    if (-not (Test-Path $vswhere)) {
        return $null
    }
    $path = & $vswhere -latest -products * `
        -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
        -property installationPath 2>$null
    if ($path -and (Test-Path $path)) {
        return $path.Trim()
    }
    return $null
}

Require-Command git "Install Git from https://git-scm.com/"
Require-Command cmake "Install: winget install Kitware.CMake then reopen the terminal."

$vsPath = Get-VsInstallPath
if (-not $vsPath) {
    Write-Error "Visual Studio C++ tools not found. Install VS Build Tools or VS Community with Desktop C++ workload, then reopen the terminal."
}

$vcvars = Join-Path $vsPath "VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path -LiteralPath $vcvars)) {
    Write-Error "vcvars64.bat missing under: $vsPath"
}

New-Item -ItemType Directory -Force -Path $ThirdParty | Out-Null

if (-not (Test-Path (Join-Path $WhisperDir ".git"))) {
    Write-Host "[whisper.cpp] Cloning into third_party..."
    git clone --depth 1 --branch $WhisperCppRef https://github.com/ggerganov/whisper.cpp.git $WhisperDir
} else {
    Write-Host "[whisper.cpp] Updating existing clone..."
    Push-Location $WhisperDir
    try {
        git fetch --depth 1 origin $WhisperCppRef 2>$null
        git checkout $WhisperCppRef 2>$null
        git pull --ff-only 2>$null
    } finally {
        Pop-Location
    }
}

if ($Clean -and (Test-Path $BuildDir)) {
    Remove-Item -Recurse -Force $BuildDir
}

$vulkanOk = $false
if ($env:VULKAN_SDK -and (Test-Path -LiteralPath $env:VULKAN_SDK)) {
    $vulkanOk = $true
    Write-Host "[whisper.cpp] VULKAN_SDK=$($env:VULKAN_SDK)"
} else {
    Write-Warning "VULKAN_SDK is not set. Install Vulkan SDK, reopen terminal, then rebuild with -Clean."
}

$generators = @(
    "Visual Studio 18 2026",
    "Visual Studio 17 2022",
    "Visual Studio 16 2019"
)

$cmakeFlags = @(
    "-S", $WhisperDir,
    "-B", $BuildDir,
    "-DGGML_VULKAN=ON",
    "-DBUILD_SHARED_LIBS=OFF",
    "-DWHISPER_BUILD_TESTS=OFF"
)

$configured = $false
$usedGenerator = $null
foreach ($gen in $generators) {
    Write-Host "[whisper.cpp] Trying CMake generator: $gen"
    if (Test-Path $BuildDir) {
        Remove-Item -Recurse -Force $BuildDir -ErrorAction SilentlyContinue
    }
    $configureCmd = "call `"$vcvars`" >nul && cmake $($cmakeFlags -join ' ') -G `"$gen`" -A x64"
    cmd /c $configureCmd
    if ($LASTEXITCODE -eq 0) {
        $configured = $true
        $usedGenerator = $gen
        break
    }
}

if (-not $configured) {
    Write-Error "CMake configure failed. Use Developer PowerShell for VS or repair the C++ workload."
}

Write-Host "[whisper.cpp] Configured with: $usedGenerator"
Write-Host "[whisper.cpp] Building Release (several minutes)..."
$buildCmd = "call `"$vcvars`" >nul && cmake --build `"$BuildDir`" --config Release --target whisper-cli"
cmd /c $buildCmd
if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed. Install Vulkan SDK (core), reopen terminal, run with -Clean."
}

$cliCandidates = @(
    (Join-Path $BuildDir "bin\Release\whisper-cli.exe"),
    (Join-Path $BuildDir "bin\whisper-cli.exe"),
    (Join-Path $BuildDir "Release\whisper-cli.exe")
)
$cli = $cliCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $cli) {
    Write-Error "whisper-cli.exe not found under $BuildDir"
}

Write-Host ""
Write-Host "[whisper.cpp] OK: $cli"
if (-not $vulkanOk) {
    Write-Warning "Vulkan SDK was missing at configure time; GPU offload may not work."
}
Write-Host ""
Write-Host "Next:"
Write-Host "  .\tools\spike_whisper_vulkan.ps1 -SkipBuild"
Write-Host "  `$env:BUZZMINI_BACKEND='vulkan'"
Write-Host "  `$env:BUZZMINI_WHISPER_CLI='$cli'"
