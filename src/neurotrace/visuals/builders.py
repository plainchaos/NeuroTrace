from __future__ import annotations

from typing import Any, Dict


def normalize_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "message_count": int(raw.get("message_count") or 0),
        "start_ts": float(raw.get("start_ts") or 0.0),
        "end_ts": float(raw.get("end_ts") or 0.0),
        "zones": list(raw.get("zones") or []),
    }


