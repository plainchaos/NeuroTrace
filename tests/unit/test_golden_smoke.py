from __future__ import annotations

from pathlib import Path
import sqlite3
import sys


def _add_cli_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


_add_cli_to_path()

from typer.testing import CliRunner
from neurotrace.cli import app


runner = CliRunner()


def test_golden_smoke_ingest_end_to_end(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    seed = repo_root / "tests/fixtures/seed/canonical_export_snippet.json"
    db = tmp_path / "conversations.db"

    # Run ingest CLI
    result = runner.invoke(app, ["ingest", "--input", str(seed), "--db", str(db)])
    assert result.exit_code == 0

    # Validate DB minimally
    conn = sqlite3.connect(str(db))
    try:
        cur = conn.execute("SELECT COUNT(*) FROM messages")
        assert cur.fetchone()[0] >= 1
        cur = conn.execute("SELECT COUNT(*) FROM message_contents")
        assert cur.fetchone()[0] >= 1
    finally:
        conn.close()

    # Ensure duplicates manifest exists
    manifest = repo_root / "outputs/validation/manifest.json"
    assert manifest.exists()
