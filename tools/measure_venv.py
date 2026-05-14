"""One-off: print largest dirs under .venv/Lib/site-packages. Run from repo root."""
from __future__ import annotations

from pathlib import Path


def dir_size(p: Path) -> int:
    total = 0
    if not p.exists():
        return 0
    for f in p.rglob("*"):
        try:
            if f.is_file():
                total += f.stat().st_size
        except OSError:
            pass
    return total


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    venv = root / ".venv"
    if not venv.exists():
        print("NO .venv at", venv)
        return
    sp = venv / "Lib" / "site-packages"
    rows: list[tuple[int, str]] = []
    if sp.exists():
        for child in sp.iterdir():
            if child.is_dir():
                rows.append((dir_size(child), child.name))
            elif child.is_file():
                rows.append((child.stat().st_size, child.name))
    rows.sort(reverse=True)
    print("Top site-packages (MB):")
    for sz, name in rows[:40]:
        print(f"{sz / 1024 / 1024:8.1f}  {name}")
    print()
    print(f"site-packages total: {dir_size(sp) / 1024 / 1024:.1f} MB")
    print(f".venv total: {dir_size(venv) / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
