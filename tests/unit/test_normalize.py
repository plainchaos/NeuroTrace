from __future__ import annotations

from pathlib import Path
import json
import sys


def _add_src_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_src_to_path()

from neurotrace.ingest.load_raw import load_export  # noqa: E402
from neurotrace.ingest.normalize import normalize_messages  # noqa: E402


def test_normalize_yields_records_and_manifest(tmp_path, monkeypatch):
    # Use real seed to run normalization
    repo_root = Path(__file__).resolve().parents[2]
    seed = repo_root / "tests/fixtures/seed/canonical_export_snippet.json"
    raw = load_export(str(seed))

    # Redirect outputs/validation to a tmp location by monkeypatching Path if needed
    # Simpler: run and then check default location in repo
    records = list(normalize_messages(raw))
    assert len(records) > 0
    # Ensure required fields exist
    sample = records[0]
    for key in [
        "id",
        "raw_id",
        "conversation_id",
        "gizmo_id",
        "parent_id",
        "role",
        "created_at",
        "content_text",
        "content_type",
        "attachments_json",
        "meta_json",
    ]:
        assert key in sample

    manifest_path = repo_root / "outputs/validation/manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "duplicates" in manifest
