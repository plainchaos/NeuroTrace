from __future__ import annotations

import pandas as pd


def length_buckets(summary_wide: pd.DataFrame) -> pd.DataFrame:
    """Return DataFrame with columns: bucket,count for conversation lengths."""
    if summary_wide.empty or "n_messages" not in summary_wide:
        return pd.DataFrame(columns=["bucket", "count"])
    lengths = summary_wide["n_messages"].fillna(0).astype(int)
    labels = ["<=10", "11-20", "21-50", "51-100", "101-200", "201-500", "501-1000", ">1000"]
    counts = {k: 0 for k in labels}
    for v in lengths.tolist():
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
    return pd.DataFrame([{"bucket": k, "count": v} for k, v in counts.items()])


def depth_histogram(breadcrumbs: pd.DataFrame) -> pd.DataFrame:
    """
    Placeholder: If depth metrics are available (e.g., response depth module),
    compute histogram. Without that, return empty.
    """
    return pd.DataFrame(columns=["depth", "count"])



