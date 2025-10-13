from __future__ import annotations

from typing import Any, Dict, Iterable, List


def compute_metrics(sessions: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    sessions_list: List[Dict[str, Any]] = list(sessions)
    num_sessions = len(sessions_list)
    num_messages = sum(len(s.get("messages", [])) for s in sessions_list)
    return {
        "sessions": num_sessions,
        "messages": num_messages,
    }
