from __future__ import annotations

from pathlib import Path
import sys


def _add_repo_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_repo_to_path()

from typer.testing import CliRunner
from neurotrace.cli import app  # standardized import path


runner = CliRunner()


def test_cli_validate_runs():
    repo_root = Path(__file__).resolve().parents[2]
    seed = repo_root / "tests/fixtures/seed/canonical_export_snippet.json"
    result = runner.invoke(app, ["validate", "--input", str(seed)])
    assert result.exit_code == 0


essential_db = "cli_test.db"


def test_cli_ingest_runs(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    seed = repo_root / "tests/fixtures/seed/canonical_export_snippet.json"
    db = tmp_path / essential_db
    result = runner.invoke(app, ["ingest", "--input", str(seed), "--db", str(db)])
    assert result.exit_code == 0
    assert db.exists()
