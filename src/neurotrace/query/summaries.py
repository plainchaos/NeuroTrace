from __future__ import annotations

import sqlite3
from typing import Any, Dict


def build_materialized_views(conn: sqlite3.Connection) -> None:
    """Create lightweight temp views for stable rollups.

    These are read-only helpers that do not persist state.
    """
    with conn:
        conn.execute(
            """
            CREATE TEMP VIEW IF NOT EXISTS v_messages AS
            SELECT id, conversation_id, role, parent_id, create_time
            FROM messages
            """
        )
        conn.execute(
            """
            CREATE TEMP VIEW IF NOT EXISTS v_session_firsts AS
            SELECT conversation_id, MIN(create_time) AS first_ts
            FROM v_messages
            WHERE conversation_id IS NOT NULL
            GROUP BY conversation_id
            """
        )


def session_summary(conn: sqlite3.Connection, session_id: str) -> Dict[str, Any]:
    """Return a deterministic per-session rollup."""
    build_materialized_views(conn)
    cur = conn.execute(
        """
        SELECT
          COUNT(*) AS message_count,
          MIN(create_time) AS start_ts,
          MAX(create_time) AS end_ts
        FROM v_messages
        WHERE conversation_id = ?
        """,
        (session_id,),
    )
    row = cur.fetchone() or (0, None, None)
    return {
        "session_id": session_id,
        "message_count": row[0],
        "start_ts": row[1],
        "end_ts": row[2],
    }


