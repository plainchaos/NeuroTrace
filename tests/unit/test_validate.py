from __future__ import annotations

from pathlib import Path
import sys


def _add_src_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_src_to_path()

from neurotrace.ingest.load_raw import load_export  # noqa: E402
from neurotrace.ingest.validate import validate_raw_export  # noqa: E402


def test_validate_seed_report_basic_counts():
    repo_root = Path(__file__).resolve().parents[2]
    seed = repo_root / "tests/fixtures/seed/canonical_export_snippet.json"
    raw = load_export(str(seed))
    report = validate_raw_export(raw)
    assert isinstance(report, dict)
    assert report.get("num_conversations", 0) >= 1
    assert report.get("num_messages_total", 0) >= 1
    assert report.get("orphans", 0) >= 0
    assert "attachments_summary" in report
