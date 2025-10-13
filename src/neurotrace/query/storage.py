from __future__ import annotations

import sqlite3
from typing import Any, Dict, Iterable, Iterator, Optional, Tuple


def open_db(path: str, *, read_only: bool = True) -> sqlite3.Connection:
    """Open a SQLite database connection in read-only mode by default.

    Uses URI mode for read-only to prevent accidental writes.
    """
    if read_only:
        uri = f"file:{path}?mode=ro"
        return sqlite3.connect(uri, uri=True)
    return sqlite3.connect(path)


def _rows_to_dicts(cursor: sqlite3.Cursor) -> Iterator[Dict[str, Any]]:
    columns = [d[0] for d in cursor.description or []]
    for row in cursor:
        yield {col: row[idx] for idx, col in enumerate(columns)}


def fetch_messages(
    conn: sqlite3.Connection,
    where: Optional[str] = None,
    params: Tuple[Any, ...] = (),
    limit: Optional[int] = None,
) -> Iterable[Dict[str, Any]]:
    """Fetch messages with optional WHERE clause parameters.

    Ordering is stable by create_time, then role, then id to aid determinism.
    """
    sql = (
        "SELECT id, conversation_id, role, parent_id, create_time, content_type, children_ids "
        "FROM messages"
    )
    if where:
        sql += f" WHERE {where}"
    sql += " ORDER BY create_time ASC, role ASC, id ASC"
    if limit is not None:
        sql += " LIMIT ?"
        params = (*params, limit)
    cur = conn.execute(sql, params)
    return list(_rows_to_dicts(cur))


def fetch_distinct_conversations(
    conn: sqlite3.Connection,
    limit: Optional[int] = None,
) -> Iterable[str]:
    """Return distinct conversation ids derived from messages."""
    sql = "SELECT DISTINCT conversation_id FROM messages WHERE conversation_id IS NOT NULL ORDER BY conversation_id"
    if limit is not None:
        sql += " LIMIT ?"
        cur = conn.execute(sql, (limit,))
    else:
        cur = conn.execute(sql)
    return [r[0] for r in cur.fetchall()]


def fetch_message_contents(
    conn: sqlite3.Connection,
    message_id: str,
) -> Iterable[Dict[str, Any]]:
    """Fetch message content parts for the given message id."""
    sql = (
        "SELECT message_id, part_index, content "
        "FROM message_contents WHERE message_id = ? ORDER BY part_index ASC"
    )
    cur = conn.execute(sql, (message_id,))
    return list(_rows_to_dicts(cur))


def fetch_sessions(
    conn: sqlite3.Connection,
    *,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Iterable[Dict[str, Any]]:
    """Return lightweight session rows with id and basic counts.

    Matches blueprint contract: read-only and deterministic ordering.
    """
    sql = (
        "SELECT conversation_id AS id, COUNT(*) AS message_count, "
        "MIN(create_time) AS start_ts, MAX(create_time) AS end_ts "
        "FROM messages WHERE conversation_id IS NOT NULL "
        "GROUP BY conversation_id ORDER BY conversation_id"
    )
    params: Tuple[Any, ...] = ()
    if limit is not None:
        sql += " LIMIT ?"
        params += (limit,)
    if offset is not None and offset:
        sql += " OFFSET ?"
        params += (offset,)
    cur = conn.execute(sql, params)
    return list(_rows_to_dicts(cur))


