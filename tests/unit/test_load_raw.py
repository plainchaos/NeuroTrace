from __future__ import annotations

from pathlib import Path
import json
import zipfile
import sys


def _add_src_to_path() -> None:
    # Ensure src/ is importable without editable install
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_src_to_path()

from neurotrace.ingest.load_raw import load_export  # noqa: E402


def test_load_export_json_seed():
    seed = Path(__file__).resolve().parents[2] / "tests/fixtures/seed/canonical_export_snippet.json"
    assert seed.exists(), f"Missing seed file: {seed}"
    data = load_export(str(seed))
    assert isinstance(data, dict)
    assert len(data) > 0


def test_load_export_zip(tmp_path):
    # Create a zip containing a copy of the seed JSON
    repo_root = Path(__file__).resolve().parents[2]
    seed = repo_root / "tests/fixtures/seed/canonical_export_snippet.json"
    zpath = tmp_path / "seed.zip"
    with zipfile.ZipFile(zpath, mode="w") as zf:
        zf.writestr("export.json", seed.read_text(encoding="utf-8"))
    data = load_export(str(zpath))
    assert isinstance(data, dict)
    assert len(data) > 0
