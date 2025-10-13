from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Tuple


def _infer_zone(message: Dict[str, Any]) -> str:
    # Prefer an explicit zone if present; else fall back to role as a proxy
    z = (message.get("zone") or message.get("function") or message.get("role") or "unknown").strip()
    return str(z).lower() or "unknown"


def compute_zone_mix_and_transitions(sessions: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compute overall zone mix and pairwise transitions across sessions.

    Input sessions are dicts with at least {"messages": [ {role|zone|function, ...}, ... ]}.
    The message order is preserved as provided.
    """
    zone_counts: Counter[str] = Counter()
    trans_counts: Counter[Tuple[str, str]] = Counter()

    for session in sessions:
        messages: List[Dict[str, Any]] = list(session.get("messages", []))
        if not messages:
            continue
        zones = [_infer_zone(m) for m in messages]
        for z in zones:
            zone_counts[z] += 1
        for a, b in zip(zones, zones[1:]):
            trans_counts[(a, b)] += 1

    zone_mix = [{"zone": z, "count": int(c)} for z, c in sorted(zone_counts.items(), key=lambda x: x[0])]
    transitions = [
        {"from": a, "to": b, "count": int(c)}
        for (a, b), c in sorted(trans_counts.items(), key=lambda x: (x[0][0], x[0][1]))
    ]
    return zone_mix, transitions


