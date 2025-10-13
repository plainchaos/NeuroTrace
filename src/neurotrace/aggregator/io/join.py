from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd

from .scan import _ensure_path


def _read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def load_breadcrumbs(metrics_root: Path | str, ids: Iterable[str]) -> pd.DataFrame:
    root = _ensure_path(metrics_root)
    rows: List[pd.DataFrame] = []
    for cid in ids:
        df = _read_csv_optional(root / "breadcrumbs" / f"{cid}.csv")
        if not df.empty:
            df = df.assign(conversation_id=cid)
            # Keep only the blueprint columns if present
            cols = [c for c in ["idx", "timestamp", "role", "parent_id", "top_zone", "preview", "conversation_id"] if c in df.columns]
            df = df[cols]
            rows.append(df)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def load_summary_wide(metrics_root: Path | str, ids: Iterable[str]) -> pd.DataFrame:
    """
    Load long-form summary (metric,value) per conversation and pivot to wide form:
    one row per conversation_id with columns [n_messages, n_user, n_assistant, zone_*].
    """
    root = _ensure_path(metrics_root)
    frames: List[pd.DataFrame] = []
    for cid in ids:
        df = _read_csv_optional(root / "summary" / f"{cid}.csv")
        if df.empty:
            continue
        if "metric" in df.columns and "value" in df.columns:
            pv = (
                df[["metric", "value"]]
                .assign(conversation_id=cid)
                .pivot(index="conversation_id", columns="metric", values="value")
                .reset_index()
            )
            frames.append(pv)
        else:
            # Already wide: ensure conversation_id present
            df = df.assign(conversation_id=cid)
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True).fillna(0)
    # Ensure expected columns exist (fill if missing)
    expected = [
        "n_messages", "n_user", "n_assistant",
        "zone_Planning", "zone_Response", "zone_Memory", "zone_Feedback", "zone_Reflection", "zone_Unknown",
    ]
    for col in expected:
        if col not in out.columns:
            out[col] = 0
    # Reorder columns
    cols = ["conversation_id"] + expected + [c for c in out.columns if c not in {"conversation_id", *expected}]
    return out[cols]


def load_transitions(metrics_root: Path | str, ids: Iterable[str]) -> pd.DataFrame:
    root = _ensure_path(metrics_root)
    frames: List[pd.DataFrame] = []
    for cid in ids:
        df = _read_csv_optional(root / "transitions" / f"{cid}.csv")
        if not df.empty:
            # normalize column names if needed
            rename_map = {"from": "from_zone", "to": "to_zone"}
            df = df.rename(columns=rename_map)
            keep = [c for c in ["from_zone", "to_zone", "count"] if c in df.columns]
            df = df[keep].assign(conversation_id=cid)
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def join_all(metrics_root: Path | str, ids: Iterable[str]) -> Dict[str, pd.DataFrame]:
    """Convenience loader returning a dict of DataFrames keyed by section name."""
    return {
        "breadcrumbs": load_breadcrumbs(metrics_root, ids),
        "summary": load_summary_wide(metrics_root, ids),
        "transitions": load_transitions(metrics_root, ids),
    }



