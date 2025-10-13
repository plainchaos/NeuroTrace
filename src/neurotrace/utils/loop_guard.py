from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def log_fingerprint(agent: str, action: str, payload: Dict[str, Any]) -> Path:
    repo = Path(__file__).resolve().parents[3]
    log_path = repo / "Cursor_Agent_Management" / "logs" / "loop_fingerprints.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {"agent": agent, "action": action, **payload}
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return log_path


