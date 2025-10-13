from __future__ import annotations

from typing import Dict
import pandas as pd


def compute_transition_matrix(transitions: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Row-normalized transition counts into probabilities per from_zone."""
    if transitions.empty:
        return {}
    df = transitions.copy()
    # ensure required columns
    for c in ("from_zone", "to_zone", "count"):
        if c not in df.columns:
            return {}
    grouped = df.groupby("from_zone")
    matrix: Dict[str, Dict[str, float]] = {}
    for from_zone, g in grouped:
        total = g["count"].sum()
        row: Dict[str, float] = {}
        if total > 0:
            for _, r in g.iterrows():
                row[str(r["to_zone"]) or "Unknown"] = float(r["count"]) / float(total)
        matrix[str(from_zone) or "Unknown"] = row
    return matrix


