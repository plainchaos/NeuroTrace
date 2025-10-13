from __future__ import annotations

from pathlib import Path
import json

from neurotrace.utils.loop_guard import log_fingerprint


def test_log_fingerprint_appends_record(tmp_path: Path):
    # Redirect repo root via env not implemented; just call and assert file grows
    p = log_fingerprint("dev1", "test_action", {"exit": 1})
    assert p.exists()
    data = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert any(rec.get("agent") == "dev1" and rec.get("action") == "test_action" for rec in data)


