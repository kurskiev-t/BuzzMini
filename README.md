<p align="center">
  <img src="assets/logo.svg" width="800" height="400" alt="BuzzMini" />
</p>

# BuzzMini

Локальное распознавание речи «на лету»: нажал горячие клавиши — продиктовал — текст вставился в активное окно (буфер обмена + симуляция вставки). Работает через **faster-whisper** и **PyTorch**; при наличии NVIDIA GPU транскрипция идёт на видеокарте.

Идея — минимальный Push-to-talk без облака, в духе Buzz, но проще и под свой сценарий.

## Возможности

- Иконка в системном трее, запись по удержанию комбинации из двух клавиш (по умолчанию **левый Ctrl + пробел**; в **Settings** можно выбрать левый/правый Ctrl и вторую клавишу — пробел или Win/Cmd/Super). Переменная `BUZZMINI_PTT_CHORD` переопределяет выбор.
- Выбор модели Whisper и загрузка с Hugging Face (в трее: **Models…**).
- Микрофон и аккорд PTT в **Settings**.
- Диалог **Donate — Донат** в меню трея — поддержка проекта (ВТБ Paymo, QR; см. ниже).

## Требования

- **Python 3.12–3.14**
- Windows / Linux / macOS (GPU на Windows чаще всего через CUDA-сборку PyTorch).
- Для GPU: драйвер NVIDIA и в venv должен стоять **`torch` с CUDA** (не путать с колёсом **CPU-only** с PyPI). Системный `python` или один лишь `pip install -e .` без отдельного шага для Windows часто дают **CPU** `torch` → в логах будет `torch.cuda=False`.

### Это не «LLM для чата»

В BuzzMini под капотом **Whisper** (распознавание речи в текст), через **faster-whisper** + **CTranslate2**. Отдельной большой языковой модели для диалогов нет: один выбранный вес Whisper грузится в память и обрабатывает аудио.

### Модели в диалоге «Models…» и железо

В списке доступны те же размеры, что и у типичного OpenAI Whisper (варианты **`.en`** — только английский, обычно чуть компактнее по задаче):

| Модель (id) | Ориентировочный размер на диске | Заметка |
|---------------|----------------------------------|--------|
| **Tiny** / **Tiny.En** | ~75 МБ | Быстро даже на CPU, качество ниже. |
| **Base** / **Base.En** | ~150 МБ | Разумный минимум для повседневных тестов. |
| **Small** / **Small.En** | ~500 МБ | Баланс скорости и качества на CPU. |
| **Medium** / **Medium.En** | ~1,5 ГБ | Комфортнее при **≥8 ГБ** RAM на CPU. |
| **Large** (`large-v1`) | ~3 ГБ | Тяжелее по RAM/VRAM. |
| **Large-V2** | ~3 ГБ | |
| **Large-V3** | ~3 ГБ | |
| **Large-V3-Turbo** | ~1,5–2,5 ГБ | Быстрее «полного» large-v3, хороший компромисс. |

**Windows / Linux с NVIDIA:** при CUDA 12+ и `torch` с CUDA движок по умолчанию идёт на **GPU** (`cuda`). Ориентир по **VRAM** (зависит от драйвера и `compute_type`): *tiny/base* — от порядка **1 ГБ**; *small* — ~**2 ГБ**; *medium* — ~**4–6 ГБ**; *large* / *v2* / *v3* — часто **8 ГБ и больше** комфортнее. Меньше VRAM — см. `BUZZMINI_REDUCE_VRAM` / `BUZZ_REDUCE_GPU_MEMORY` в коде (режим экономии).

**macOS (в т.ч. Mac Pro / MacBook):** в текущей версии движок faster-whisper запускается на **CPU** (Apple GPU через Metal **не** подключён к этому пути). Это нормально: *tiny* / *base* / *small* работают заметно быстрее, *medium* и тем более *large* — дольше; для Mac Pro с большим объёмом RAM удобнее не гнаться за самым большим весом без нужды. PTT с **Cmd** как второй клавишей поддерживается (см. настройки / `BUZZMINI_PTT_CHORD`).

## Установка и запуск

Рекомендуется виртуальное окружение в корне репозитория.

### Через uv

```bash
cd BuzzMini
uv sync
uv run buzz-mini
```

### Через pip

**Важно (Windows + NVIDIA):** `pip install -e .` **одной командой** почти всегда ставит **`torch` с PyPI без CUDA** (как у вас: `torch-2.x.x-cp314-win_amd64.whl` с pypi.org → `torch.cuda=False`). Настройки **`[tool.uv.sources]`** в `pyproject.toml` учитывает только **`uv`**, не `pip`.

Варианты:

1. **Рекомендуется:** раздел **«Через uv»** выше — там под Windows подставляется wheel **cu126** автоматически.

2. **Через pip:** сначала CUDA-сборный `torch`, потом проект (или переустановите `torch`, если уже поставили `-e .`):

```bat
cd BuzzMini
python -m venv .venv
.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cu126
.venv\Scripts\python.exe -m pip install -e .
```

Если вы уже сделали `pip install -e .` и видите CPU:

```bat
.venv\Scripts\python.exe -m pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu126
```

### Запуск приложения

**Windows — быстрый старт:** после `uv sync` можно просто запустить двойным щелчком **`scripts\run-buzz-mini.bat`**

Всегда используйте интерпретатор из того же venv, куда ставили зависимости:

```bat
cd BuzzMini
.\.venv\Scripts\python.exe -m buzz_mini.app
```


После `pip install -e .` можно также вызывать консольную команду `buzz-mini`, если активирован нужный venv.

### Где лежат модели

По умолчанию при запуске **из исходников** кэш моделей — папка **`models`** в корне репозитория (рядом с `pyproject.toml`). Иначе используется пользовательский кэш приложения и совместимость с каталогом Buzz.

Переопределение:

- `BUZZMINI_MODEL_ROOT` — свой каталог для весов и HF-снимков.

### Полезные переменные окружения

| Переменная | Назначение |
|------------|------------|
| `BUZZMINI_MODEL` | Модель по умолчанию (если не выбрано в настройках). |
| `BUZZMINI_LANGUAGE` | Язык распознавания, например `ru`. |
| `BUZZMINI_PTT_CHORD` | Аккорд из двух клавиш, например `ctrl_l+space`, `ctrl_r+win`; также принимается `ctrl+space` (как у Handy) — это левый Ctrl + пробел. |
| `BUZZMINI_FORCE_CPU` | Не `false` — принудительно CPU. |
| `BUZZMINI_DEVICE` | `cuda`, `cpu` или `auto`. |
| `BUZZMINI_PASTE_DELAY_MS` | Задержка перед симуляцией вставки после записи в буфер (мс). |
| `BUZZMINI_LOG_LEVEL` | Уровень логирования, например `DEBUG`. |

## Smoke-тест без GUI

Проверяет импорты, диалог моделей без показа, движок `tiny` и разбор строк PTT (удобно для будущего CI).

```bat
cd BuzzMini
.\.venv\Scripts\python.exe tools\smoke_test.py
```

Если пакет не установлен в editable-режиме, задайте `PYTHONPATH` на корень репозитория (каталог с `pyproject.toml`).

## Поддержать проект

Разработка ведётся в свободное время. Если BuzzMini пригодился, можно поддержать автора (**Тимур К.**) переводом через **ВТБ (Paymo)**:

- **Ссылка:** [страница сбора](https://vtb.paymo.ru/collect-money/?transaction=f77f0675-61b6-4914-bca1-97a2eff8c32d)
- **QR** (удобно с телефона):

![QR доната ВТБ](assets/donate-qr.png)

В приложении: меню трея → **Donate — Донат** — там же текст, ссылка и этот QR.

Профиль на **Donatty** сейчас на проверке; когда он будет доступен, в окне доната и здесь появится и второй вариант.
