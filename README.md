<p align="center">
  <img src="assets/logo.svg" width="800" height="400" alt="BuzzMini" />
</p>

**English** | [Русский](README.ru.md)

# BuzzMini

Hold a hotkey, speak, release — the text is pasted where the cursor is.

Offline push-to-talk for **Windows**, **Linux**, and **macOS**. No cloud, no subscription. Speech is recognized on this PC with [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

**[Download for Windows (Setup.exe)](https://github.com/kurskiev-t/BuzzMini/releases/latest)**

<!-- Drop a 5–10s clip at assets/demo.gif (Notepad or Telegram → hold Ctrl+Space → speak → text appears) and uncomment:
![Demo](assets/demo.gif)
-->

## Why BuzzMini?

| | |
|--|--|
| **Vs Windows dictation** | Stronger on Russian, no Microsoft cloud services, works without an online account. |
| **Vs original [Buzz](https://github.com/chidiwilliams/buzz)** | One job: dictate into any window. Lives in the tray, no extra workspace of windows. |
| **Privacy** | Audio never leaves the machine — not Yandex, Google, or OpenAI. |

Default chord: **Left Ctrl + Space**. Change it in **Settings**. NVIDIA GPU (CUDA) is used when available; otherwise CPU.

This is **speech-to-text**, not a chat LLM. One Whisper model is loaded and turns audio into text.

## Install (Windows)

1. Open **[Releases](https://github.com/kurskiev-t/BuzzMini/releases/latest)** and download **`BuzzMini-Setup-*.exe`**.
2. Run the installer. The app starts in the **system tray**.
3. Tray → **Models…** → pick a model → **Download**, then **Apply selection and reload model**. For Russian, **Small** or **Medium** is a solid start; **Large-V3-Turbo** if you have the RAM/VRAM.
4. Click into any text field, **hold** the chord, speak, **release**. The transcript is pasted immediately.

Whisper weights are downloaded on first use (Hugging Face, with a GitHub release mirror as fallback) — not bundled in Setup.exe.

**AMD / Intel GPUs** are not used; transcription stays on **CPU** — prefer Tiny / Base / Small.

## Features

- Tray icon; record while holding a two-key chord (left/right Ctrl + Space or Win/Cmd).
- Model picker and download in **Models…**.
- Microphone and chord in **Settings**.
- **Donate** in the tray — [CloudTips](https://pay.cloudtips.ru/p/3fbf7934).

<details>
<summary>Models, disk size, and VRAM</summary>

Same sizes as typical OpenAI Whisper (**.en** = English-only):

| Model (id) | Approx. disk | Notes |
|--------------|----------------|--------|
| **Tiny** / **Tiny.En** | ~75 MB | Fast on CPU; lower quality. |
| **Base** / **Base.En** | ~150 MB | Everyday minimum. |
| **Small** / **Small.En** | ~500 MB | Good CPU balance. |
| **Medium** / **Medium.En** | ~1.5 GB | Better with **≥8 GB** RAM on CPU. |
| **Large** (`large-v1`) / **V2** / **V3** | ~3 GB | Heavier RAM/VRAM. |
| **Large-V3-Turbo** | ~1.5–2.5 GB | Faster than full large-v3. |

**Windows / Linux + NVIDIA:** CUDA 12+ and a CUDA build of `torch` → device `cuda`. Rough **VRAM**: tiny/base ~1 GB; small ~2 GB; medium ~4–6 GB; large often 8 GB+. Tight VRAM: `BUZZMINI_REDUCE_VRAM` / `BUZZ_REDUCE_GPU_MEMORY`.

**macOS:** faster-whisper runs on **CPU** (no Metal path here). Tiny / base / small are the practical choices. Cmd as the second PTT key is supported.

</details>

<details>
<summary>Linux, macOS, and run from source (Python, uv, pip)</summary>

Python **3.12–3.14**. Use a venv in the repo root.

### uv (recommended)

```bash
cd BuzzMini
uv sync
uv run buzz-mini
```

On Windows, uv pulls the **cu126** PyTorch wheel via `[tool.uv.sources]` in `pyproject.toml`.

### pip

A plain `pip install -e .` on Windows usually installs **CPU-only** `torch` (`torch.cuda=False`). Install CUDA `torch` first:

```bat
cd BuzzMini
python -m venv .venv
.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu126
.venv\Scripts\python.exe -m pip install -e .
```

Already installed CPU torch:

```bat
.venv\Scripts\python.exe -m pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu126
```

### Launch

**Windows:** double-click **`scripts\run-buzz-mini.bat`** — creates `.venv` if needed, installs PyTorch cu126, `pip install -e .`, starts the tray app.

If the env is ready:

```bat
cd BuzzMini
.\.venv\Scripts\python.exe -m buzz_mini.app
```

Or `buzz-mini` with the venv activated.

### Where models are stored

From source: **`models/`** next to `pyproject.toml`. Installed app: user cache (compatible with Buzz’s directory). Override: `BUZZMINI_MODEL_ROOT`.

### Environment variables

| Variable | Purpose |
|----------|---------|
| `BUZZMINI_MODEL` | Default model if unset in the UI. |
| `BUZZMINI_LANGUAGE` | Recognition language, e.g. `ru`. |
| `BUZZMINI_PTT_CHORD` | Two-key chord, e.g. `ctrl_l+space`, `ctrl_r+win`; `ctrl+space` = left Ctrl + Space. |
| `BUZZMINI_FORCE_CPU` | Anything other than `false` forces CPU. |
| `BUZZMINI_DEVICE` | `cuda`, `cpu`, or `auto`. |
| `BUZZMINI_PASTE_DELAY_MS` | Delay before paste after clipboard write (ms). |
| `BUZZMINI_LOG_LEVEL` | e.g. `DEBUG`. |

</details>

<details>
<summary>Windows build and installer (maintainers)</summary>

**PyInstaller (dev):** `BuzzMini.spec` + `tools/build_windows.ps1`. Same `.venv` with CUDA PyTorch; optional extra `win-build`. Output: `dist/BuzzMini/` (`BuzzMini.exe`, several GB).

**NSIS web installer** — two GitHub Release assets:

| File | Build with | Purpose |
|------|------------|---------|
| **`BuzzMini-<version>-win64.7z`** | `.\tools\build_release_payload.ps1` | PyInstaller onedir, downloaded at install time |
| **`BuzzMini-Setup-<version>.exe`** | `.\tools\build_installer.ps1` | Small installer (fetches the `.7z`) |

Release checklist:

1. `.\tools\build_windows.ps1` → `dist\BuzzMini\`
2. [7-Zip](https://www.7-zip.org/) and [NSIS](https://nsis.sourceforge.io/) (`winget install NSIS.NSIS`)
3. `.\tools\build_release_payload.ps1` → `dist\BuzzMini-1.1.0-win64.7z` (name from `installer\release.json`)
4. GitHub Release tag **`1.1.0`** (no `v` prefix), attach the `.7z`
5. `.\tools\build_installer.ps1` → `dist\BuzzMini-Setup-1.1.0.exe`, attach to the same release

Installing shows the GitHub URL, download, and extract under **Show details**. Whisper weights still come from **Models**, not the installer.

URL config: `installer\release.json`. Overrides on `build_installer.ps1`: `-PayloadUrl`, `-GithubRepo`, `-ProductVersion`.

</details>

<details>
<summary>Headless smoke test</summary>

Imports, models UI without showing, `tiny` engine, PTT chord parsing:

```bat
cd BuzzMini
.\.venv\Scripts\python.exe tools\smoke_test.py
```

If the package is not installed editable, set `PYTHONPATH` to the repo root.

</details>

## Support the project

Spare-time work. If BuzzMini helps, support **Timur K.** via **[CloudTips](https://pay.cloudtips.ru/p/3fbf7934)** (Russian cards, SBP, and other methods on the page).

In the app: tray → **Donate**, or the **Donate** tab.
