from __future__ import annotations

import sqlite3
from typing import Any, Dict
from pathlib import Path
import json
import re


def run_privacy_audit(conn: sqlite3.Connection, sample_limit: int = 1000) -> Dict[str, Any]:
    """Scan message contents for basic PII markers (rule-based v1).

    Returns status OK when no markers are found in the sampled rows.
    """
    email_re = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    phone_re = re.compile(r"(?:(?:\+\d{1,3}[\s-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s-]?\d{3,4}[\s-]?\d{3,4})")
    url_re = re.compile(r"https?://[\w.-]+(?:/[\w\-./?%&=]*)?")

    cur = conn.execute(
        "SELECT content FROM message_contents ORDER BY message_id, part_index LIMIT ?",
        (sample_limit,),
    )
    total = 0
    hits = {"email": 0, "phone": 0, "url": 0}
    for (text,) in cur.fetchall():
        total += 1
        t = text or ""
        if email_re.search(t):
            hits["email"] += 1
        if phone_re.search(t):
            hits["phone"] += 1
        if url_re.search(t):
            hits["url"] += 1

    found = sum(hits.values())
    status = "OK" if found == 0 else "FAIL"
    result: Dict[str, Any] = {"status": status, "records_scanned": total, "hits": hits}
    # Write audit log per blueprint
    out_dir = Path("outputs/privacy")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


