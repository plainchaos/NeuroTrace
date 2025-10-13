from __future__ import annotations

import sqlite3
from pathlib import Path
from importlib.resources import files
from typing import Any, Dict, Iterable


def _ensure_schema(conn: sqlite3.Connection) -> None:
    # Load bundled schema via package resources; fallback to repo path if needed.
    try:
        # Access bundled resource relative to the top-level package
        sql = (files("neurotrace") / "schema" / "create.sql").read_text(encoding="utf-8")
    except Exception:
        ddl_path = Path("schema/create.sql")
        sql = ddl_path.read_text(encoding="utf-8")
    with conn:
        conn.executescript(sql)


def write_sqlite(records: Iterable[Dict[str, Any]], metrics: Dict[str, Any], db_path: str) -> None:
    dbp = Path(db_path)
    conn = sqlite3.connect(str(dbp))
    try:
        _ensure_schema(conn)
        with conn:
            for r in records:
                # messages core columns per schema
                conn.execute(
                    """
                    INSERT OR REPLACE INTO messages (
                      id, conversation_id, role, parent_id, gizmo_id, create_time,
                      content_type, children_ids
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        r.get("id"),
                        r.get("conversation_id"),
                        r.get("role"),
                        r.get("parent_id"),
                        r.get("gizmo_id") or "_orphan",
                        r.get("created_at"),
                        r.get("content_type"),
                        "[]",
                    ),
                )
                # message_contents
                text = r.get("content_text") or ""
                conn.execute(
                    """
                    INSERT OR REPLACE INTO message_contents (
                      message_id, part_index, content
                    ) VALUES (?, ?, ?)
                    """,
                    (
                        r.get("id"),
                        0,
                        text,
                    ),
                )
        # Note: metrics table is not defined in schema/create.sql; skipping DB write for metrics
    finally:
        conn.close()


def json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
