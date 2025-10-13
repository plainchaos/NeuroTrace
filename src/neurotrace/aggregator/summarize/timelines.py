from __future__ import annotations

from typing import Dict
import pandas as pd


def coverage_over_time(breadcrumbs: pd.DataFrame) -> pd.DataFrame:
    """Compute daily coverage (assistant non-Unknown share) by date."""
    if breadcrumbs.empty or "timestamp" not in breadcrumbs.columns:
        return pd.DataFrame(columns=["date", "coverage"])
    df = breadcrumbs.copy()
    # ensure datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])  # drop rows without timestamps
    df["date"] = df["timestamp"].dt.date.astype(str)
    # assistant-only rows for coverage calc
    df_a = df[df["role"] == "assistant"].copy()
    if df_a.empty:
        return pd.DataFrame(columns=["date", "coverage"])
    grp = df_a.groupby("date")
    out = []
    for date, g in grp:
        a = len(g)
        unknown = int(((g["top_zone"].isna()) | (g["top_zone"] == "Unknown")).sum())
        share = (a - unknown) / a if a > 0 else 0.0
        out.append({"date": str(date), "coverage": float(share)})
    return pd.DataFrame(out).sort_values(by="date")


def roles_over_time(breadcrumbs: pd.DataFrame) -> pd.DataFrame:
    """Compute daily counts of roles (assistant, user)."""
    if breadcrumbs.empty or "timestamp" not in breadcrumbs.columns:
        return pd.DataFrame(columns=["date", "assistant", "user", "tool_system"])
    df = breadcrumbs.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])  # drop rows without timestamps
    df["date"] = df["timestamp"].dt.date.astype(str)
    grp = df.groupby(["date", "role"]).size().unstack(fill_value=0)
    grp = grp.reset_index().rename_axis(None, axis=1)
    # ensure columns present
    for col in ["assistant", "user"]:
        if col not in grp.columns:
            grp[col] = 0
    grp["tool_system"] = 0
    return grp[["date", "assistant", "user", "tool_system"]].sort_values(by="date")



