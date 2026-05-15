"""CI: install [project] dependencies from pyproject.toml except torch (torch: CPU wheel in workflow)."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path


def _canonical_name(spec: str) -> str:
    head = spec.strip().split(";", 1)[0].strip()
    if "[" in head:
        head = head.split("[", 1)[0].strip()
    return head.split()[0].strip().lower().replace("-", "_")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_specs_without_torch() -> list[str]:
    data = tomllib.loads((_repo_root() / "pyproject.toml").read_text(encoding="utf-8"))
    deps: list[str] = list(data["project"]["dependencies"])
    return [d for d in deps if _canonical_name(d) != "torch"]


def main() -> None:
    specs = runtime_specs_without_torch()
    subprocess.check_call([sys.executable, "-m", "pip", "install", *specs])


if __name__ == "__main__":
    main()
