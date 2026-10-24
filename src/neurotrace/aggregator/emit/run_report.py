from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Tuple, List, Any
import hashlib
import json
import logging

from ..summarize.rollups import compute_scale, compute_zones
from ..summarize.timelines import coverage_over_time, roles_over_time
from ..summarize.buckets import length_buckets, depth_histogram
from ..quality.coverage import compute_coverage_metrics
from ..quality.transitions import compute_transition_matrix


logger = logging.getLogger("neurotrace.aggregator")


def _iso_now() -> str:
    # Same output as the old utcnow() form (naive ISO + "Z"), without the deprecated call.
    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat() + "Z"


def _hash_bytes(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def _hash_json(obj: Any) -> str:
    return _hash_bytes(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def _write_json(path: Path, obj: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")


def build_run_report(
    metrics_root: Path | str,
    *,
    code_version: str = "mvp1+report-v0.1",
    generated_at: str | None = None,
) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, Any]]:
    """
    Build run_report JSON structure and return (report_dict, file_hashes) where
    file_hashes is a mapping for charts to be written by write_charts().
    """
    from ..io.scan import discover_conversations
    from ..io.join import join_all

    root = Path(metrics_root)
    ids = discover_conversations(root)
    joined = join_all(root, ids)

    breadcrumbs = joined["breadcrumbs"]
    summary = joined["summary"]
    transitions = joined["transitions"]

    meta = {
        "code_version": code_version,
        "source_dir": str(root),
        "conversations_total": int(len(ids)),
        "date_range": _compute_date_range(breadcrumbs),
    }
    if generated_at:
        meta["generated_at"] = generated_at

    scale = compute_scale(summary)
    zones = compute_zones(summary)
    matrix = compute_transition_matrix(transitions)
    depth = {"mean_of_means": 0.0, "median": 0.0, "p90": 0, "p95": 0, "max": 0, "outlier_policy": "cap visual at 30; annotate agentic loops"}
    cov_q = compute_coverage_metrics(breadcrumbs)

    quality = {
        "index_mismatch": {"index_count": int(len(ids)), "actual": int(summary.shape[0])},
        "unknown_only_examples": [],
        "absolute_paths_present": True,
        "timestamps_with_nan": cov_q["timestamps_with_nan"],
        "agentic_share": cov_q["assistant_non_unknown_share_mean"],
    }

    report = {
        "meta": meta,
        "scale": scale,
        "zones": zones,
        "transitions": {"matrix": matrix, "notes": "proportions of exits from each zone"},
        "depth": depth,
        "quality": quality,
        "recommendations": [
            "emit run_manifest.json",
            "use relative paths",
            "tag tool/system outputs",
            "segment metrics with/without agentic",
        ],
    }

    # Charts (hash content to return for manifest)
    charts_payloads = _build_charts_payloads(summary, breadcrumbs, transitions)
    chart_hashes = {rel: _hash_json(payload) for rel, payload in charts_payloads.items()}

    return report, chart_hashes, charts_payloads


# -------- Derived JSON first (single source of truth) -----------------------------------------

def _load_json_optional(p: Path) -> object:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def _matrix_from_transitions_list(transitions: List[Dict[str, object]]) -> Dict[str, Dict[str, float]]:
    # Row-normalize counts into probabilities per source zone
    from collections import defaultdict

    rows: Dict[str, Dict[str, float]] = {}
    counts = defaultdict(lambda: defaultdict(int))
    for item in transitions or []:
        a = str(item.get("from"))
        b = str(item.get("to"))
        c = int(item.get("count") or 0)
        counts[a][b] += c
    for a, row in counts.items():
        total = float(sum(row.values())) or 1.0
        rows[a] = {b: (v / total) for b, v in sorted(row.items(), key=lambda kv: kv[0])}
    return rows


def build_run_report_from_derived(
    derived_root: Path | str,
    run_id: str,
    *,
    code_version: str = "mvp1+report-v0.2",
    generated_at: str | None = None,
) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, Any]]:
    root = Path(derived_root)
    troot = root / "transitions" / run_id
    droot = root / "depth" / run_id
    mroot = root / "metrics" / run_id

    zone_mix = _load_json_optional(troot / "zone_mix.json") or []
    transitions_raw = _load_json_optional(troot / "transitions.json") or []
    depth = _load_json_optional(droot / "depth_dist.json") or []
    metrics_payload = _load_json_optional(mroot / "metrics.json") or {}

    summary_block: Dict[str, Any] = {}
    sessions_metrics: Dict[str, Any] = {}
    if isinstance(metrics_payload, dict):
        if isinstance(metrics_payload.get("summary"), dict):
            summary_block = metrics_payload.get("summary", {})
        else:
            summary_block = {
                "sessions": metrics_payload.get("sessions"),
                "messages": metrics_payload.get("messages"),
            }
        if isinstance(metrics_payload.get("sessions"), dict):
            sessions_metrics = metrics_payload.get("sessions", {})

    messages_total = int(summary_block.get("messages") or 0)
    sessions_total = int(summary_block.get("sessions") or 0)

    zones_totals = {str(item.get("zone")): int(item.get("count") or 0) for item in (zone_mix or [])}
    dominant_counts = _dominant_zone_counts(sessions_metrics)
    coverage_mean, coverage_median = _coverage_stats(sessions_metrics)

    matrix = _matrix_from_transitions_list(transitions_raw or [])

    meta = {
        "code_version": code_version,
        "source_dir": str(root),
    }
    if generated_at:
        meta["generated_at"] = generated_at

    scale = {"sessions_total": sessions_total, "messages_total": messages_total}
    zones = {
        "totals": zones_totals,
        "coverage": {
            "assistant_non_unknown_share_mean": coverage_mean,
            "assistant_non_unknown_share_median": coverage_median,
        },
        "dominant_zone_counts": dominant_counts,
    }

    quality = {
        "index_mismatch": {"index_count": sessions_total, "actual": sessions_total},
        "unknown_only_examples": [],
        "absolute_paths_present": False,
        "timestamps_with_nan": 0,
        "agentic_share": coverage_mean,
    }

    report = {
        "meta": meta,
        "scale": scale,
        "zones": zones,
        "transitions": {"matrix": matrix, "notes": "proportions of exits from each zone"},
        "depth": {"hist": depth},
        "quality": quality,
        "recommendations": [
            "emit run_manifest.json",
            "use relative paths",
            "tag tool/system outputs",
            "segment metrics with/without agentic",
        ],
    }

    charts_payloads: Dict[str, Any] = {
        "charts/zone_totals.json": [
            {"zone": zone, "count": count} for zone, count in sorted(zones_totals.items())
        ],
        "charts/transition_matrix.json": matrix,
        "charts/depth_hist.json": [
            {"depth": int(item.get("depth") or 0), "count": int(item.get("count") or 0)}
            for item in (depth or [])
        ],
        "charts/coverage_over_time.json": [],
        "charts/roles_over_time.json": [],
        "charts/dominant_zone_per_convo.json": _dominant_zone_rows(sessions_metrics),
        "charts/length_buckets.json": _length_buckets_from_sessions(sessions_metrics),
    }

    chart_hashes = {rel: _hash_json(payload) for rel, payload in charts_payloads.items()}

    return report, chart_hashes, charts_payloads


def _compute_date_range(breadcrumbs: pd.DataFrame) -> list[str]:
    if breadcrumbs.empty or "timestamp" not in breadcrumbs:
        return ["", ""]
    ts = pd.to_datetime(breadcrumbs["timestamp"], errors="coerce").dropna()
    if ts.empty:
        return ["", ""]
    return [str(ts.min().date()), str(ts.max().date())]


def _build_charts_payloads(summary: "pd.DataFrame", breadcrumbs: "pd.DataFrame", transitions: "pd.DataFrame") -> Dict[str, object]:
    import pandas as pd  # local import to avoid mandatory dependency when unused

    zone_totals_df = _zones_totals_df(summary)
    length_df = length_buckets(summary)
    depth_df = depth_histogram(breadcrumbs)
    coverage_df = coverage_over_time(breadcrumbs)
    roles_df = roles_over_time(breadcrumbs)
    dominant_df = _dominant_zone_df(summary)
    matrix = _matrix_json(transitions)

    return {
        "charts/zone_totals.json": _df_to_records(zone_totals_df),
        "charts/length_buckets.json": _df_to_records(length_df),
        "charts/transition_matrix.json": matrix,
        "charts/depth_hist.json": _df_to_records(depth_df),
        "charts/coverage_over_time.json": _df_to_records(coverage_df),
        "charts/roles_over_time.json": _df_to_records(roles_df),
        "charts/dominant_zone_per_convo.json": _df_to_records(dominant_df),
    }


def _zones_totals_df(summary: pd.DataFrame) -> pd.DataFrame:
    from ..summarize.rollups import compute_zones
    z = compute_zones(summary)["totals"]
    return pd.DataFrame([{"zone": k, "count": v} for k, v in z.items()])


def _matrix_json(transitions: pd.DataFrame) -> Dict:
    from ..quality.transitions import compute_transition_matrix
    return compute_transition_matrix(transitions)


def _dominant_zone_df(summary: pd.DataFrame) -> pd.DataFrame:
    zones = [c for c in summary.columns if c.startswith("zone_")]
    rows = []
    for _, row in summary.iterrows():
        if not zones:
            continue
        sub = {c: int(row.get(c, 0)) for c in zones}
        dom = max(sub, key=sub.get)
        rows.append({"conversation_id": row.get("conversation_id"), "dominant_zone": dom.replace("zone_", "")})
    return pd.DataFrame(rows)


def _df_to_records(df: "pd.DataFrame") -> List[Dict[str, Any]]:
    if df.empty:
        return []
    # Ensure deterministic ordering
    cols = list(df.columns)
    records = df.to_dict(orient="records")
    ordered: List[Dict[str, Any]] = []
    for rec in records:
        ordered.append({col: rec.get(col) for col in cols})
    return ordered


def _dominant_zone_counts(session_metrics: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    if not isinstance(session_metrics, dict):
        return counts
    for data in session_metrics.values():
        mix = data.get("zone_mix") if isinstance(data, dict) else None
        if not isinstance(mix, dict) or not mix:
            continue
        dominant = sorted(
            ((str(zone), float(value)) for zone, value in mix.items()),
            key=lambda item: (-item[1], item[0]),
        )[0][0]
        counts[dominant] = counts.get(dominant, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: kv[0]))


def _dominant_zone_rows(session_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not isinstance(session_metrics, dict):
        return rows
    for conv_id, data in sorted(session_metrics.items(), key=lambda kv: kv[0]):
        mix = data.get("zone_mix") if isinstance(data, dict) else None
        if not isinstance(mix, dict) or not mix:
            continue
        dominant = sorted(
            ((str(zone), float(value)) for zone, value in mix.items()),
            key=lambda item: (-item[1], item[0]),
        )[0][0]
        rows.append({"conversation_id": conv_id, "dominant_zone": dominant})
    return rows


def _coverage_stats(session_metrics: Dict[str, Any]) -> Tuple[float, float]:
    shares: List[float] = []
    if isinstance(session_metrics, dict):
        for data in session_metrics.values():
            mix = data.get("zone_mix") if isinstance(data, dict) else None
            if not isinstance(mix, dict) or not mix:
                continue
            total = sum(float(v) for v in mix.values())
            if total <= 0:
                continue
            non_unknown = sum(
                float(v)
                for zone, v in mix.items()
                if str(zone).lower() not in {"unknown", ""}
            )
            shares.append(non_unknown / total)
    if not shares:
        return 0.0, 0.0
    shares.sort()
    mean = sum(shares) / len(shares)
    median = shares[len(shares) // 2] if len(shares) % 2 == 1 else (
        shares[len(shares) // 2 - 1] + shares[len(shares) // 2]
    ) / 2
    return float(mean), float(median)


def _length_buckets_from_sessions(session_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    buckets = ["<=10", "11-20", "21-50", "51-100", "101-200", "201-500", "501-1000", ">1000"]
    counts = {bucket: 0 for bucket in buckets}
    if isinstance(session_metrics, dict):
        for data in session_metrics.values():
            volume = None
            if isinstance(data, dict):
                volume = data.get("volume")
                if volume is None and isinstance(data.get("metrics"), dict):
                    volume = data["metrics"].get("volume")
            try:
                n = int(volume) if volume is not None else None
            except Exception:
                n = None
            if n is None:
                continue
            if n <= 10:
                counts["<=10"] += 1
            elif n <= 20:
                counts["11-20"] += 1
            elif n <= 50:
                counts["21-50"] += 1
            elif n <= 100:
                counts["51-100"] += 1
            elif n <= 200:
                counts["101-200"] += 1
            elif n <= 500:
                counts["201-500"] += 1
            elif n <= 1000:
                counts["501-1000"] += 1
            else:
                counts[">1000"] += 1
    return [{"bucket": bucket, "count": counts[bucket]} for bucket in buckets]


def write_report_and_charts(metrics_root: Path | str, out_root: Path | str = Path("outputs/report")) -> Dict[str, str]:
    """Legacy CSV path: build report and charts from outputs/metrics/* CSVs.

    Kept for backward compatibility. New flows should call write_report_and_charts_from_derived.
    """
    generated_at = _iso_now()
    report, chart_hashes, charts = build_run_report(metrics_root, generated_at=None)
    out = Path(out_root)
    # Write report
    _write_json(out / "run_report.json", report)
    for rel, payload in charts.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")

    # Manifest
    manifest = {
        "run_id": generated_at,
        "hashes": {"run_report.json": _hash_bytes((out / "run_report.json").read_bytes())} | chart_hashes,
        "selection": "full",
        "code_version": "mvp1+report-v0.1",
        "generated_at": generated_at,
    }
    _write_json(out / "run_manifest.json", manifest)
    return {"report": str(out / "run_report.json"), "manifest": str(out / "run_manifest.json")}


def write_report_and_charts_from_derived(derived_root: Path | str, run_id: str, out_root: Path | str = Path("outputs/report")) -> Dict[str, str]:
    """Build report and charts from derived JSON artifacts for a given run_id."""
    out = Path(out_root)
    generated_at = _iso_now()
    report, chart_hashes, charts = build_run_report_from_derived(derived_root, run_id, generated_at=None)
    # Write report
    _write_json(out / "run_report.json", report)
    # Write charts (JSON only)
    for rel, payload in charts.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")

    manifest = {
        "run_id": run_id,
        "hashes": {"run_report.json": _hash_bytes((out / "run_report.json").read_bytes())} | chart_hashes,
        "selection": "full",
        "code_version": "mvp1+report-v0.2",
        "generated_at": generated_at,
    }
    _write_json(out / "run_manifest.json", manifest)
    return {"report": str(out / "run_report.json"), "manifest": str(out / "run_manifest.json")}
