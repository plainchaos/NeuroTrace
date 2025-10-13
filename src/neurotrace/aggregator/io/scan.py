from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def _ensure_path(p: Path | str) -> Path:
    return p if isinstance(p, Path) else Path(p)


def discover_conversations(metrics_root: Path | str) -> List[str]:
    """
    Discover conversation IDs by intersecting filenames present in
    outputs/metrics/{breadcrumbs,summary}.

    Only IDs that have both breadcrumbs and summary are returned. Transitions
    are optional at this stage and may be computed/aggregated separately.
    """
    root = _ensure_path(metrics_root)
    bdir = root / "breadcrumbs"
    sdir = root / "summary"

    if not bdir.exists() or not sdir.exists():
        return []

    def stems(d: Path) -> set[str]:
        return {p.stem for p in d.glob("*.csv")}

    have_breadcrumbs = stems(bdir)
    have_summary = stems(sdir)

    return sorted(have_breadcrumbs & have_summary)


def validate_presence(metrics_root: Path | str, ids: Iterable[str] | None = None) -> Dict[str, List[str]]:
    """
    Validate presence of expected files for each conversation ID.

    Returns a dict with keys: missing_breadcrumbs, missing_summary, missing_transitions.
    If `ids` is None, uses discover_conversations() union of stems from all dirs.
    """
    root = _ensure_path(metrics_root)
    bdir = root / "breadcrumbs"
    sdir = root / "summary"
    tdir = root / "transitions"

    def stems(d: Path) -> set[str]:
        return {p.stem for p in d.glob("*.csv")}

    have_b = stems(bdir) if bdir.exists() else set()
    have_s = stems(sdir) if sdir.exists() else set()
    have_t = stems(tdir) if tdir.exists() else set()

    all_ids = set(ids) if ids is not None else (have_b | have_s | have_t)

    missing_b = sorted([i for i in all_ids if i not in have_b])
    missing_s = sorted([i for i in all_ids if i not in have_s])
    missing_t = sorted([i for i in all_ids if i not in have_t])

    return {
        "missing_breadcrumbs": missing_b,
        "missing_summary": missing_s,
        "missing_transitions": missing_t,
    }



