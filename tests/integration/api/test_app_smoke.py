from __future__ import annotations

from pathlib import Path
import sys

from fastapi.testclient import TestClient


def _add_repo_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_repo_to_path()

from neurotrace.api.http import build_app  # noqa: E402
from neurotrace.query.storage import open_db  # noqa: E402


def test_app_health_and_session_endpoints(tmp_path):
    # Build a tiny DB from seed via CLI is heavier; instead create minimal tables
    db = tmp_path / "smoke.db"
    import sqlite3

    with sqlite3.connect(db) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
              id TEXT PRIMARY KEY,
              conversation_id TEXT,
              role TEXT,
              parent_id TEXT,
              gizmo_id TEXT DEFAULT '_orphan',
              create_time REAL,
              content_type TEXT,
              children_ids TEXT
            );
            INSERT INTO messages(id, conversation_id, role, parent_id, create_time, content_type, children_ids)
            VALUES ('m1','s1','user',NULL,1.0,'text','[]'), ('m2','s1','assistant','m1',2.0,'text','[]');
            """
        )

    app = build_app(str(db))
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"schema_hash", "golden_hash", "version"}

    r = client.get("/sessions?limit=100&offset=0")
    assert r.status_code == 200
    sessions = r.json()
    assert isinstance(sessions, list) and len(sessions) == 1
    assert set(sessions[0].keys()) == {"id", "started_at", "message_count"}
    assert sessions[0]["id"] == "s1"

    r = client.get("/sessions/s1")
    assert r.status_code == 200
    assert r.json()["message_count"] == 2

    r = client.get("/sessions/s1/tree")
    assert r.status_code == 200

    r = client.get("/sessions/s1/visuals/overview")
    assert r.status_code == 200
    r = client.get("/sessions/s1/visuals/zone_mix")
    assert r.status_code == 200
    r = client.get("/sessions/s1/visuals/depth_dist")
    assert r.status_code == 200
    r = client.get("/sessions/s1/visuals/transitions")
    assert r.status_code == 200

