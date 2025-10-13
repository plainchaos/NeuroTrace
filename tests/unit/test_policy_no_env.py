from __future__ import annotations

from pathlib import Path


def test_no_env_usage_in_package():
    repo_root = Path(__file__).resolve().parents[2]
    pkg = repo_root / "src" / "neurotrace"
    bad = []
    for p in pkg.rglob("*.py"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if "os.environ" in txt or ".getenv(" in txt:
            bad.append(str(p))
    assert not bad, f"Disallowed env usage found: {bad}"

