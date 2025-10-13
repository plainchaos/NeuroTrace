from __future__ import annotations

from typing import Any, Dict
import hashlib
import json


def hash_json(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def determinism_ok(payloads: Dict[str, Any], expected_hashes: Dict[str, str]) -> bool:
    return all(hash_json(payloads[k]) == expected_hashes[k] for k in expected_hashes)



