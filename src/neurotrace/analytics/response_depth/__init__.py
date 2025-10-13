from __future__ import annotations

from typing import Any, Dict, Iterable, List


def compute_depth_distribution(sessions: Iterable[Dict[str, Any]]) -> List[Dict[str, int]]:
    """Compute a simple depth distribution based on message order per session.

    For each session, count the index (1-based) of assistant messages and aggregate across sessions.
    """
    counts: Dict[int, int] = {}
    for session in sessions:
        messages: List[Dict[str, Any]] = list(session.get("messages", []))
        depth = 0
        for msg in messages:
            if (msg.get("role") or "").lower() == "assistant":
                depth += 1
                counts[depth] = counts.get(depth, 0) + 1
    # Emit sorted by depth
    return [{"depth": d, "count": c} for d, c in sorted(counts.items(), key=lambda x: x[0])]
