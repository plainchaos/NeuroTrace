from __future__ import annotations

from typing import Dict, List
import pandas as pd


def compute_coverage_metrics(breadcrumbs: pd.DataFrame) -> Dict:
    """
    Returns:
      - timestamps_with_nan: count of missing/invalid timestamps
      - assistant_non_unknown_share_mean/median (same as zones.coverage basis)
    """
    if breadcrumbs.empty:
        return {
            "timestamps_with_nan": 0,
            "assistant_non_unknown_share_mean": 0.0,
            "assistant_non_unknown_share_median": 0.0,
        }

    ts = pd.to_datetime(breadcrumbs.get("timestamp"), errors="coerce")
    ts_missing = int(ts.isna().sum())

    df_a = breadcrumbs[breadcrumbs.get("role") == "assistant"].copy()
    shares: List[float] = []
    if not df_a.empty:
        if "conversation_id" in df_a.columns:
            grouped = df_a.groupby("conversation_id")
            for _, g in grouped:
                a = len(g)
                unknown = int(((g["top_zone"].isna()) | (g["top_zone"] == "Unknown")).sum())
                shares.append((a - unknown) / a if a > 0 else 0.0)
        else:
            a = len(df_a)
            unknown = int(((df_a["top_zone"].isna()) | (df_a["top_zone"] == "Unknown")).sum())
            shares.append((a - unknown) / a if a > 0 else 0.0)
    s = pd.Series(shares)
    return {
        "timestamps_with_nan": ts_missing,
        "assistant_non_unknown_share_mean": float(s.mean()) if not s.empty else 0.0,
        "assistant_non_unknown_share_median": float(s.median()) if not s.empty else 0.0,
    }


