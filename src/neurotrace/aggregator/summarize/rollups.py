from __future__ import annotations

from typing import Dict, List
import pandas as pd


def compute_scale(summary_wide: pd.DataFrame) -> Dict:
    if summary_wide.empty:
        return {
            "messages_total": 0,
            "by_role": {"assistant": 0, "user": 0, "tool_system": 0},
            "length": {"median": 0.0, "mean": 0.0, "buckets": {}},
            "top5_conversations_by_messages": [],
        }

    # totals
    messages_total = int(summary_wide["n_messages"].sum()) if "n_messages" in summary_wide else 0
    n_assistant = int(summary_wide["n_assistant"].sum()) if "n_assistant" in summary_wide else 0
    n_user = int(summary_wide["n_user"].sum()) if "n_user" in summary_wide else 0

    # length per conversation approximated by n_messages
    lengths = summary_wide.get("n_messages", pd.Series(dtype=float))
    median_len = float(lengths.median()) if not lengths.empty else 0.0
    mean_len = float(lengths.mean()) if not lengths.empty else 0.0

    # buckets
    bucket_edges = [10, 20, 50, 100, 200, 500, 1000]
    labels: List[str] = ["<=10", "11-20", "21-50", "51-100", "101-200", "201-500", "501-1000", ">1000"]
    counts = {k: 0 for k in labels}
    for v in lengths.fillna(0).astype(int).tolist():
        if v <= 10:
            counts["<=10"] += 1
        elif v <= 20:
            counts["11-20"] += 1
        elif v <= 50:
            counts["21-50"] += 1
        elif v <= 100:
            counts["51-100"] += 1
        elif v <= 200:
            counts["101-200"] += 1
        elif v <= 500:
            counts["201-500"] += 1
        elif v <= 1000:
            counts["501-1000"] += 1
        else:
            counts[">1000"] += 1

    top5 = (
        summary_wide.sort_values(by="n_messages", ascending=False)["conversation_id"].head(5).astype(str).tolist()
        if "n_messages" in summary_wide and "conversation_id" in summary_wide
        else []
    )

    return {
        "messages_total": messages_total,
        "by_role": {"assistant": n_assistant, "user": n_user, "tool_system": 0},
        "length": {"median": median_len, "mean": mean_len, "buckets": counts},
        "top5_conversations_by_messages": top5,
    }


def compute_zones(summary_wide: pd.DataFrame) -> Dict:
    zones = ["Planning", "Response", "Feedback", "Memory", "Reflection", "Unknown"]
    totals = {}
    for z in zones:
        col = f"zone_{z}"
        totals[z] = int(summary_wide.get(col, pd.Series(dtype=int)).sum()) if not summary_wide.empty else 0

    # assistant_non_unknown_share: assistant turns minus Unknown over assistant turns
    if summary_wide.empty or "n_assistant" not in summary_wide:
        coverage_mean = 0.0
        coverage_median = 0.0
    else:
        per_conv = []
        for _, row in summary_wide.iterrows():
            a = int(row.get("n_assistant", 0))
            unknown = int(row.get("zone_Unknown", 0))
            share = (a - unknown) / a if a > 0 else 0.0
            per_conv.append(share)
        s = pd.Series(per_conv)
        coverage_mean = float(s.mean()) if not s.empty else 0.0
        coverage_median = float(s.median()) if not s.empty else 0.0

    # dominant zone per conversation
    dom_counts: Dict[str, int] = {z: 0 for z in zones if z != "Unknown"}
    if not summary_wide.empty:
        zone_cols = [f"zone_{z}" for z in zones]
        zone_cols = [c for c in zone_cols if c in summary_wide.columns]
        for _, row in summary_wide.iterrows():
            if not zone_cols:
                continue
            sub = {c: int(row.get(c, 0)) for c in zone_cols}
            if not sub:
                continue
            dom_col = max(sub, key=sub.get)
            dom_zone = dom_col.replace("zone_", "")
            if dom_zone != "Unknown":
                dom_counts[dom_zone] = dom_counts.get(dom_zone, 0) + 1

    return {
        "totals": totals,
        "coverage": {
            "assistant_non_unknown_share_mean": coverage_mean,
            "assistant_non_unknown_share_median": coverage_median,
        },
        "dominant_zone_counts": dom_counts,
    }



