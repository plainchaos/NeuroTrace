from __future__ import annotations

import sqlite3
from typing import Any, Dict


def rollup_session(conn: sqlite3.Connection, session_id: str) -> Dict[str, Any]:
    """Compute simple per-session rollups.

    Uses read-only queries over the canonical schema.
    """
    cur = conn.execute(
        """
        SELECT
          COUNT(*) AS message_count,
          MIN(create_time) AS start_ts,
          MAX(create_time) AS end_ts
        FROM messages
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


