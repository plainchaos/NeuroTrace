from __future__ import annotations

import sqlite3
from typing import Dict, Any, List


def weekly_cohort_counts(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Aggregate message counts by ISO week per session (UTC)."""
    sql = (
        "SELECT conversation_id, strftime('%Y-W%W', create_time, 'unixepoch') AS week, COUNT(*) AS n "
        "FROM messages WHERE conversation_id IS NOT NULL GROUP BY conversation_id, week ORDER BY week, conversation_id"
    )
    cur = conn.execute(sql)
    return [
        {"conversation_id": r[0], "week": r[1], "count": r[2]}
        for r in cur.fetchall()
    ]


def monthly_cohort_counts(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Aggregate message counts by month per session (UTC)."""
    sql = (
        "SELECT conversation_id, strftime('%Y-%m', create_time, 'unixepoch') AS month, COUNT(*) AS n "
        "FROM messages WHERE conversation_id IS NOT NULL GROUP BY conversation_id, month ORDER BY month, conversation_id"
    )
    cur = conn.execute(sql)
    return [
        {"conversation_id": r[0], "month": r[1], "count": r[2]}
        for r in cur.fetchall()
    ]


