from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Dict
from datetime import datetime, timezone


def export_training_pack(conn: sqlite3.Connection, out_dir: str) -> Dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Minimal export (extend per blueprint)
    # sessions.jsonl (one per conversation)
    cur = conn.execute("SELECT DISTINCT conversation_id FROM messages WHERE conversation_id IS NOT NULL ORDER BY conversation_id")
    sessions = [r[0] for r in cur.fetchall()]
    (out / "sessions.jsonl").write_text("\n".join(json.dumps({"conversation_id": sid}) for sid in sessions), encoding="utf-8")

    # records.jsonl (minimal fields per message)
    cur = conn.execute(
        "SELECT id, conversation_id, role, parent_id, create_time FROM messages ORDER BY conversation_id, create_time, id"
    )
    records_n = 0
    with (out / "records.jsonl").open("w", encoding="utf-8") as f:
        for mid, cid, role, pid, ts in cur.fetchall():
            f.write(json.dumps({
                "id": mid,
                "conversation_id": cid,
                "role": role,
                "parent_id": pid,
                "ts": ts,
            }) + "\n")
            records_n += 1
    (out / "tags.jsonl").write_text("", encoding="utf-8")
    (out / "metrics.jsonl").write_text("", encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "record_counts": {"sessions": len(sessions), "records": records_n},
        "source_commit": None,
        "privacy_profile": "pseudonymized",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


