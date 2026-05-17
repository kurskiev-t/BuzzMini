<p align="center">
  <img src="assets/logo.svg" width="800" height="400" alt="BuzzMini" />
</p>

**English** | [Русский](README.ru.md)

# BuzzMini

Local speech-to-text on the fly: hold a hotkey chord, dictate, and the text is pasted into the active window (clipboard + simulated paste). Powered by **faster-whisper** and **PyTorch**; with an **NVIDIA** GPU, transcription runs on the video card.

A minimal push-to-talk app with no cloud — inspired by Buzz, but simpler and focused on one workflow.

## Features

- System tray icon; record while holding a two-key chord (default **Left Ctrl + Space**). In **Settings** you can pick left/right Ctrl and the second key — Space or Win/Cmd/Super. Override with `BUZZMINI_PTT_CHORD`.
- Choose a Whisper model and download from Hugging Face (tray menu **Models…**).
- Microphone and PTT chord in **Settings**.
- **Donate** in the tray menu — support the project (VTB Paymo, QR; see below).

## Requirements

- **Python 3.12–3.14**
- Windows / Linux / macOS (on Windows, GPU usually means a **CUDA** build of PyTorch).
- For GPU: **NVIDIA** driver and **`torch` with CUDA** in your venv (not the **CPU-only** wheel from PyPI). A plain `pip install -e .` on Windows often yields **CPU** `torch` → logs show `torch.cuda=False`.
- **AMD / Intel GPUs:** GPU acceleration is **not supported** (NVIDIA + CUDA only). On those PCs transcription uses **CPU** — pick a smaller model (Small / Base).

### Not a chat LLM

BuzzMini uses **Whisper** (speech → text) via **faster-whisper** + **CTranslate2**. There is no separate large language model for chat: one Whisper weight is loaded and processes audio.

### Models in **Models…** and hardware

Same sizes as typical OpenAI Whisper (**`.en`** variants are English-only and often slightly leaner):

| Model (id) | Approx. disk size | Notes |
|--------------|-------------------|--------|
| **Tiny** / **Tiny.En** | ~75 MB | Fast even on CPU; lower quality. |
| **Base** / **Base.En** | ~150 MB | Reasonable minimum for everyday use. |
| **Small** / **Small.En** | ~500 MB | Good speed/quality balance on CPU. |
| **Medium** / **Medium.En** | ~1.5 GB | More comfortable with **≥8 GB** RAM on CPU. |
| **Large** (`large-v1`) | ~3 GB | Heavier on RAM/VRAM. |
| **Large-V2** | ~3 GB | |
| **Large-V3** | ~3 GB | |
| **Large-V3-Turbo** | ~1.5–2.5 GB | Faster than full large-v3; solid compromise. |

**Windows / Linux with NVIDIA:** with CUDA 12+ and CUDA `torch`, the engine defaults to **GPU** (`cuda`). Rough **VRAM** guides (driver and `compute_type` matter): *tiny/base* ~**1 GB**; *small* ~**2 GB**; *medium* ~**4–6 GB**; *large* / *v2* / *v3* often **8 GB+**. Less VRAM → see `BUZZMINI_REDUCE_VRAM` / `BUZZ_REDUCE_GPU_MEMORY` in code.

**macOS:** faster-whisper currently runs on **CPU** (Apple GPU / Metal is **not** wired to this path). *tiny* / *base* / *small* are fine; *medium* / *large* are slower. PTT with **Cmd** as the second key is supported (Settings / `BUZZMINI_PTT_CHORD`).

## Install and run

Use a virtual environment in the repo root.

### With uv

```bash
cd BuzzMini
uv sync
uv run buzz-mini
```

### With pip

**Important (Windows + NVIDIA):** a single `pip install -e .` almost always installs **CPU-only** `torch` from PyPI (`torch.cuda=False`). The **`[tool.uv.sources]`** block in `pyproject.toml` applies to **`uv` only**, not plain `pip`.

Options:

1. **Recommended:** the **uv** section above — on Windows it picks the **cu126** wheel automatically.

2. **pip:** install CUDA `torch` first, then the project (or reinstall `torch` if you already ran `-e .`):

```bat
cd BuzzMini
python -m venv .venv
.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu126
.venv\Scripts\python.exe -m pip install -e .
```

If you already ran `pip install -e .` and see CPU:

```bat
.venv\Scripts\python.exe -m pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu126
```

### Launch the app

**Windows:** double-click **`scripts\run-buzz-mini.bat`** — it creates `.venv` if needed, installs **PyTorch cu126**, runs **`pip install -e .`**, and starts the app (tray icon; main window via **Open Buzz Mini** or **Models / Settings / …**).

If the environment is ready (`uv sync` or manual setup):

```bat
cd BuzzMini
.\.venv\Scripts\python.exe -m buzz_mini.app
```

After `pip install -e .`, you can also run `buzz-mini` with the venv activated.

### Windows build (development, PyInstaller)

In the repo: **`BuzzMini.spec`** and **`tools/build_windows.ps1`**. Use the same **`.venv`** with **CUDA PyTorch** as for normal runs; optional extra **`win-build`** in `pyproject.toml`. Output: **`dist/BuzzMini/`** with **`BuzzMini.exe`** (several GB with dependencies).

### Windows installer (NSIS, web installer)

Two artifacts on [GitHub Releases](https://github.com/kurskiev-t/BuzzMini/releases):

| File | Build with | Purpose |
|------|------------|---------|
| **`BuzzMini-<version>-win64.7z`** | **`.\tools\build_release_payload.ps1`** | PyInstaller onedir (~GB), downloaded at install time |
| **`BuzzMini-Setup-<version>.exe`** | **`.\tools\build_installer.ps1`** | Small installer (downloads `.7z` from GitHub) |

**Release checklist:**

1. **`.\tools\build_windows.ps1`** → **`dist\BuzzMini\`**
2. Install [7-Zip](https://www.7-zip.org/) (step 3) and [NSIS](https://nsis.sourceforge.io/) (`winget install NSIS.NSIS`)
3. **`.\tools\build_release_payload.ps1`** → **`dist\BuzzMini-1.0.1-win64.7z`** (name from **`installer\release.json`**)
4. Create a GitHub Release tagged **`1.0.1`** (like [0.1.0](https://github.com/kurskiev-t/BuzzMini/releases/tag/0.1.0), no `v` prefix), attach the **`.7z`**
5. **`.\tools\build_installer.ps1`** → **`dist\BuzzMini-Setup-1.0.1.exe`**, attach to the same release

During install, **Show details** shows the GitHub URL, download progress, and extraction. **Whisper weights** are still downloaded **on first use** from the **Models** tab, not by the installer.

URL config: **`installer\release.json`** (`repository`, `tagTemplate`, `assetTemplate`). Overrides: **`-PayloadUrl`**, **`-GithubRepo`**, **`-ProductVersion`** on `build_installer.ps1`.

### Where models are stored

When running **from source**, the default cache is the **`models`** folder next to `pyproject.toml`. Otherwise the app user cache is used, with compatibility for Buzz’s model directory.

Override:

- `BUZZMINI_MODEL_ROOT` — custom directory for weights and HF snapshots.

### Useful environment variables

| Variable | Purpose |
|----------|---------|
| `BUZZMINI_MODEL` | Default model if not set in UI. |
| `BUZZMINI_LANGUAGE` | Recognition language, e.g. `ru`. |
| `BUZZMINI_PTT_CHORD` | Two-key chord, e.g. `ctrl_l+space`, `ctrl_r+win`; `ctrl+space` (Handy-style) = left Ctrl + Space. |
| `BUZZMINI_FORCE_CPU` | Anything other than `false` forces CPU. |
| `BUZZMINI_DEVICE` | `cuda`, `cpu`, or `auto`. |
| `BUZZMINI_PASTE_DELAY_MS` | Delay before paste simulation after clipboard write (ms). |
| `BUZZMINI_LOG_LEVEL` | Log level, e.g. `DEBUG`. |

## Headless smoke test

Checks imports, models UI without showing, `tiny` engine, and PTT chord parsing (handy for future CI).

```bat
cd BuzzMini
.\.venv\Scripts\python.exe tools\smoke_test.py
```

If the package is not installed editable, set `PYTHONPATH` to the repo root (folder with `pyproject.toml`).

## Support the project

Development is spare-time work. If BuzzMini helps you, you can support the author (**Timur K.**) via **VTB (Paymo)**:

- **Link:** [donation page](https://vtb.paymo.ru/collect-money/?transaction=f77f0675-61b6-4914-bca1-97a2eff8c32d)
- **QR** (easy from a phone):

![VTB donation QR](assets/donate-qr.png)

In the app: tray menu → **Donate** or the **Donate** tab — same text, link, and QR.

A **Donatty** profile is under review; a second option will appear in the donate UI and here when it goes live.
