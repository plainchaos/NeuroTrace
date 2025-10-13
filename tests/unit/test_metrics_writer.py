from __future__ import annotations

from pathlib import Path
import sqlite3
import sys


def _add_src_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_src_to_path()

from neurotrace.ingest.load_raw import load_export  # noqa: E402
from neurotrace.ingest.normalize import normalize_messages  # noqa: E402
from neurotrace.ingest.tagger import apply_tags  # noqa: E402
from neurotrace.ingest.metrics_pass import compute_session_metrics  # noqa: E402
from neurotrace.ingest.writer_sqlite import write_sqlite  # noqa: E402


def test_metrics_and_writer_sqlite(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    seed = repo_root / "tests/fixtures/seed/canonical_export_snippet.json"
    raw = load_export(str(seed))
    records = list(normalize_messages(raw))
    tagged = list(apply_tags(records))
    metrics = compute_session_metrics(tagged)

    db = tmp_path / "conversations.db"
    write_sqlite(tagged, metrics, str(db))

    # Basic checks: DB exists and has rows in messages and message_contents
    assert db.exists()
    conn = sqlite3.connect(str(db))
    try:
        cur = conn.execute("SELECT COUNT(*) FROM messages")
        n_messages = cur.fetchone()[0]
        assert n_messages >= 1
        cur = conn.execute("SELECT COUNT(*) FROM message_contents")
        n_contents = cur.fetchone()[0]
        assert n_contents >= 1
    finally:
        conn.close()
