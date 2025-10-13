from __future__ import annotations

import os
from pathlib import Path


def get_project_root() -> Path:
    """Return the project root by locating the nearest directory containing pyproject.toml.

    Falls back to the current working directory if not found.
    """
    cwd = Path(os.getcwd()).resolve()
    for parent in [cwd, *cwd.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return cwd


def get_outputs_root() -> Path:
    """Return the outputs root under the project root."""
    return get_project_root() / "outputs"


def get_derived_root() -> Path:
    """Return the derived outputs root under the project root."""
    return get_outputs_root() / "derived"


def ensure_directory(path: Path) -> None:
    """Create a directory if it does not exist (idempotent)."""
    path.mkdir(parents=True, exist_ok=True)


