from __future__ import annotations

from pathlib import Path
import pytest


@pytest.fixture(scope="session")
def seed_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    p = root / "tests" / "fixtures" / "seed" / "canonical_export_snippet.json"
    assert p.exists(), f"Missing seed file: {p}"
    return p
