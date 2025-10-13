from __future__ import annotations

from typing import Any, Dict


def vega_session_overview(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deterministic Vega-Lite spec for a simple session overview.

    Expects keys: message_count, start_ts, end_ts (timestamps as floats/ints).
    """
    message_count = int(summary.get("message_count") or 0)
    start_ts = summary.get("start_ts") or 0.0
    end_ts = summary.get("end_ts") or 0.0
    # Use Decimal from string to preserve decimal digits similar to goldens
    try:
        from decimal import Decimal
        duration_dec = Decimal(str(end_ts)) - Decimal(str(start_ts))
        duration = float(duration_dec)
    except Exception:
        duration = float(end_ts) - float(start_ts)
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": 480,
        "height": 120,
        "data": {
            "values": [
                {"metric": "message_count", "value": message_count},
                {"metric": "duration", "value": duration},
            ]
        },
        "mark": {"type": "bar"},
        "encoding": {
            "x": {"field": "metric", "type": "nominal", "sort": ["message_count", "duration"]},
            "y": {"field": "value", "type": "quantitative"}
        },
        "config": {"font": "DejaVu Sans"},
    }


def vega_zone_mix(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deterministic stacked bar spec for zone mix.

    Expects summary["zones"] = list of {"zone": str, "count": int} (optional).
    """
    zones = summary.get("zones") or []
    values = [
        {"zone": str(z.get("zone")), "count": int(z.get("count") or 0)}
        for z in zones
    ]
    values.sort(key=lambda r: (r["zone"]))
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": 480,
        "height": 160,
        "data": {"values": values},
        "mark": {"type": "bar"},
        "encoding": {
            "x": {"field": "zone", "type": "nominal", "sort": "ascending"},
            "y": {"field": "count", "type": "quantitative"},
            "color": {"field": "zone", "type": "nominal"}
        },
        "config": {"font": "DejaVu Sans"},
    }


def vega_depth_dist(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deterministic histogram spec for depth distribution.

    Expects summary["depths"] = list of {"depth": int, "count": int} (optional).
    """
    values = [
        {"depth": int(v.get("depth") or 0), "count": int(v.get("count") or 0)}
        for v in (summary.get("depths") or [])
    ]
    values.sort(key=lambda r: r["depth"])  # deterministic order
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": 480,
        "height": 160,
        "data": {"values": values},
        "mark": {"type": "bar"},
        "encoding": {
            "x": {"field": "depth", "type": "ordinal", "sort": "ascending"},
            "y": {"field": "count", "type": "quantitative"},
        },
        "config": {"font": "DejaVu Sans"},
    }


def vega_transitions(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deterministic heatmap for zone transitions.

    Expects summary["transitions"] = list of {"from": str, "to": str, "count": int}.
    Falling back to empty values if not present.
    """
    values = [
        {
            "from": str(v.get("from")),
            "to": str(v.get("to")),
            "count": int(v.get("count") or 0),
        }
        for v in (summary.get("transitions") or [])
    ]
    values.sort(key=lambda r: (r["from"], r["to"]))
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "width": 480,
        "height": 320,
        "data": {"values": values},
        "mark": {"type": "rect"},
        "encoding": {
            "x": {"field": "from", "type": "nominal", "sort": "ascending"},
            "y": {"field": "to", "type": "nominal", "sort": "ascending"},
            "color": {"field": "count", "type": "quantitative"},
        },
        "config": {"font": "DejaVu Sans"},
    }


