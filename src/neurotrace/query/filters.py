from __future__ import annotations

from typing import Tuple


def by_session(session_id: str) -> Tuple[str, tuple]:
    return ("conversation_id = ?", (session_id,))


def since(ts_utc: str) -> Tuple[str, tuple]:
    return ("created_at >= ?", (ts_utc,))



