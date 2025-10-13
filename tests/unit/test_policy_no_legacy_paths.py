from __future__ import annotations

from pathlib import Path


def test_no_legacy_path_references():
    repo_root = Path(__file__).resolve().parents[2]
    pkg = repo_root / "src" / "neurotrace"
    bad = []
    forbidden = [
        "Cursor_Agent_Management/",
        "Documentations/",
        "src/analytics/",
        "src/pipeline/",
        "src/visuals/",
        "src/graphs/",
        "src/storage_gateway/",
        "src/data_models/",
        "src/ui/",
        "src/conversation_ingestor/",
        "src/reports/",
        "src/utils/",
    ]
    for p in pkg.rglob("*.py"):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if any(s in txt for s in forbidden):
            bad.append(str(p))
    assert not bad, f"Legacy path references found: {bad}"
