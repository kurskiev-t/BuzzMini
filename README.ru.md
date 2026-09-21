<p align="center">
  <img src="assets/logo.svg" width="800" height="400" alt="BuzzMini" />
</p>

[English](README.md) | **Русский**

# BuzzMini

Зажал хоткей — надиктовал — отпустил: текст вставляется туда, где курсор.

Офлайн push-to-talk для **Windows**, **Linux** и **macOS**. Без облака и подписок. Речь распознаётся на этом компьютере через [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

**[Скачать для Windows (Setup.exe)](https://github.com/kurskiev-t/BuzzMini/releases/latest)**

<!-- Когда будет ролик 5–10 с (Блокнот или Telegram → Ctrl+Space → фраза → текст) — положите assets/demo.gif и раскомментируйте:
![Демо](assets/demo.gif)
-->

## Зачем BuzzMini?

| | |
|--|--|
| **Не системная диктовка Windows** | Русский обычно заметно лучше, не нужны облачные службы Microsoft и онлайн-аккаунт. |
| **Не оригинальный [Buzz](https://github.com/chidiwilliams/buzz)** | Одна задача: диктовать в любое окно. Живёт в трее, без лишних окон. |
| **Приватность** | Аудио никуда не уходит — ни в Яндекс, ни в Google, ни в OpenAI. |

По умолчанию аккорд: **левый Ctrl + пробел** (меняется в **Settings**). Если есть NVIDIA с CUDA — распознавание на GPU, иначе CPU.

Это **речь → текст**, не чат-LLM. Грузится один вес Whisper и обрабатывает аудио.

## Установка (Windows)

1. Откройте **[Releases](https://github.com/kurskiev-t/BuzzMini/releases/latest)** и скачайте **`BuzzMini-Setup-*.exe`**.
2. Установите. Приложение появится в **системном трее**.
3. Трей → **Models…** → выберите модель → **Download**, затем **Apply selection and reload model**. Для русского удобны **Small** или **Medium**; **Large-V3-Turbo** — если хватает RAM/VRAM.
4. Курсор в любое текстовое поле, **зажать** аккорд, сказать, **отпустить**. Текст вставляется сразу.

Веса Whisper качаются при первом использовании (Hugging Face, запасной путь — зеркало на GitHub Release), в Setup.exe их нет.

**AMD / Intel GPU** не используются: распознавание на **CPU** — берите Tiny / Base / Small.

## Возможности

- Иконка в трее; запись по удержанию двух клавиш (левый/правый Ctrl + пробел или Win/Cmd).
- Выбор и загрузка модели в **Models…**.
- Микрофон и аккорд в **Settings**.
- **Donate** в трее — [CloudTips](https://pay.cloudtips.ru/p/3fbf7934).

<details>
<summary>Модели, размер на диске и VRAM</summary>

Те же размеры, что у типичного OpenAI Whisper (**.en** — только английский):

| Модель (id) | На диске | Заметка |
|---------------|----------|--------|
| **Tiny** / **Tiny.En** | ~75 МБ | Быстро на CPU, качество ниже. |
| **Base** / **Base.En** | ~150 МБ | Разумный минимум. |
| **Small** / **Small.En** | ~500 МБ | Баланс на CPU. |
| **Medium** / **Medium.En** | ~1,5 ГБ | Комфортнее при **≥8 ГБ** RAM на CPU. |
| **Large** (`large-v1`) / **V2** / **V3** | ~3 ГБ | Тяжелее по RAM/VRAM. |
| **Large-V3-Turbo** | ~1,5–2,5 ГБ | Быстрее полного large-v3. |

**Windows / Linux + NVIDIA:** CUDA 12+ и `torch` с CUDA → устройство `cuda`. Ориентир по **VRAM**: tiny/base ~1 ГБ; small ~2 ГБ; medium ~4–6 ГБ; large часто 8 ГБ+. Мало VRAM: `BUZZMINI_REDUCE_VRAM` / `BUZZ_REDUCE_GPU_MEMORY`.

**macOS:** faster-whisper идёт на **CPU** (Metal не подключён). Практичный выбор — tiny / base / small. Cmd как вторая клавиша PTT поддерживается.

</details>

<details>
<summary>Linux, macOS и запуск из исходников (Python, uv, pip)</summary>

Нужен Python **3.12–3.14**. Виртуальное окружение — в корне репозитория.

### uv (рекомендуется)

```bash
cd BuzzMini
uv sync
uv run buzz-mini
```

На Windows uv сам берёт wheel **cu126** через `[tool.uv.sources]` в `pyproject.toml`.

### pip

Один `pip install -e .` на Windows обычно ставит **CPU-only** `torch` (`torch.cuda=False`). Сначала CUDA-сборка:

```bat
cd BuzzMini
python -m venv .venv
.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu126
.venv\Scripts\python.exe -m pip install -e .
```

Если CPU-torch уже стоит:

```bat
.venv\Scripts\python.exe -m pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu126
```

### Запуск

**Windows:** двойной щелчок по **`scripts\run-buzz-mini.bat`** — создаст `.venv` при необходимости, поставит PyTorch cu126, `pip install -e .` и запустит трей.

Если окружение уже готово:

```bat
cd BuzzMini
.\.venv\Scripts\python.exe -m buzz_mini.app
```

Или команда `buzz-mini` при активированном venv.

### Где лежат модели

Из исходников: папка **`models/`** рядом с `pyproject.toml`. У установленного приложения — пользовательский кэш (совместим с каталогом Buzz). Переопределение: `BUZZMINI_MODEL_ROOT`.

### Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `BUZZMINI_MODEL` | Модель по умолчанию, если не выбрано в UI. |
| `BUZZMINI_LANGUAGE` | Язык, например `ru`. |
| `BUZZMINI_PTT_CHORD` | Аккорд, например `ctrl_l+space`, `ctrl_r+win`; `ctrl+space` = левый Ctrl + пробел. |
| `BUZZMINI_FORCE_CPU` | Не `false` — принудительно CPU. |
| `BUZZMINI_DEVICE` | `cuda`, `cpu` или `auto`. |
| `BUZZMINI_PASTE_DELAY_MS` | Задержка перед вставкой после записи в буфер (мс). |
| `BUZZMINI_LOG_LEVEL` | Например `DEBUG`. |

</details>

<details>
<summary>Сборка Windows и установщик (для мейнтейнеров)</summary>

**PyInstaller (разработка):** `BuzzMini.spec` + `tools/build_windows.ps1`. Тот же `.venv` с CUDA PyTorch; optional extra `win-build`. Итог: `dist/BuzzMini/` (`BuzzMini.exe`, несколько ГБ).

**NSIS web-installer** — два файла на GitHub Release:

| Файл | Как собрать | Назначение |
|------|-------------|------------|
| **`BuzzMini-<версия>-win64.7z`** | `.\tools\build_release_payload.ps1` | PyInstaller onedir, качается при установке |
| **`BuzzMini-Setup-<версия>.exe`** | `.\tools\build_installer.ps1` | Маленький установщик (скачивает `.7z`) |

Порядок релиза:

1. `.\tools\build_windows.ps1` → `dist\BuzzMini\`
2. [7-Zip](https://www.7-zip.org/) и [NSIS](https://nsis.sourceforge.io/) (`winget install NSIS.NSIS`)
3. `.\tools\build_release_payload.ps1` → `dist\BuzzMini-1.1.0-win64.7z` (имя из `installer\release.json`)
4. GitHub Release с тегом **`1.1.0`** (без `v`), прикрепить `.7z`
5. `.\tools\build_installer.ps1` → `dist\BuzzMini-Setup-1.1.0.exe`, прикрепить к тому же релизу

В установщике **Show details** показывает URL, загрузку и распаковку. Веса Whisper по-прежнему из вкладки **Models**.

Конфиг URL: `installer\release.json`. Переопределения `build_installer.ps1`: `-PayloadUrl`, `-GithubRepo`, `-ProductVersion`.

</details>

<details>
<summary>Smoke-тест без GUI</summary>

Импорты, диалог моделей без показа, движок `tiny`, разбор PTT:

```bat
cd BuzzMini
.\.venv\Scripts\python.exe tools\smoke_test.py
```

Если пакет не установлен editable — задайте `PYTHONPATH` на корень репозитория.

</details>

## Поддержать проект

Разработка в свободное время. Если BuzzMini пригодился — поддержка **Тимура К.** через **[CloudTips](https://pay.cloudtips.ru/p/3fbf7934)** (карты РФ, СБП и другие способы на странице).

В приложении: трей → **Donate**, или вкладка **Donate**.
