from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List


def compute_session_metrics(records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Produce the MVP metrics payloads.

    - volume: covered (n_messages per conversation)
    - depth: partial (approximate via longest chain by parent_id)
    - zone_mix: covered (proportions per conversation if 'top_zone' present)
    - transition_matrix: covered (if 'top_zone' and sequence is available)
    - branching_factor, clarity_debt, jumpiness, stability: placeholders
    """
    # Group by conversation
    by_conv: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        conv_id = str(r.get("conversation_id", ""))
        by_conv[conv_id].append(r)

    result: Dict[str, Any] = {}

    for conv_id, msgs in by_conv.items():
        # Volume
        n_messages = len(msgs)
        # Depth: approximate via longest parent chain length
        id_to_parent: Dict[str, str] = {}
        for m in msgs:
            mid = str(m.get("id"))
            pid = m.get("parent_id")
            if pid:
                id_to_parent[mid] = str(pid)
        longest = 0
        for mid in id_to_parent.keys():
            seen = set()
            cur = mid
            depth = 1
            while cur in id_to_parent and cur not in seen:
                seen.add(cur)
                cur = id_to_parent[cur]
                depth += 1
            if depth > longest:
                longest = depth
        depth_val = longest

        # Zone mix (if present)
        zone_counts: Dict[str, int] = defaultdict(int)
        seq: List[str] = []
        for m in msgs:
            zone = None
            tags = m.get("tags")
            if isinstance(tags, list) and tags:
                zone = tags[0].get("tag")
            if zone:
                zone_counts[zone] += 1
                seq.append(zone)
        total_zones = sum(zone_counts.values())
        zone_mix = {k: (v / total_zones if total_zones else 0.0) for k, v in zone_counts.items()}

        # Transition matrix from seq
        transitions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for a, b in zip(seq, seq[1:]):
            transitions[a][b] += 1

        result[conv_id] = {
            "volume": n_messages,
            "depth": depth_val,
            "zone_mix": zone_mix,
            "transition_matrix": {src: dict(dst) for src, dst in transitions.items()},
            # Placeholders for missing metrics
            "branching_factor": None,
            "clarity_debt": None,
            "jumpiness": None,
            "stability": None,
        }

    return result
