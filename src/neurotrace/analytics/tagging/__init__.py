from __future__ import annotations

from typing import Dict, Iterable, Iterator, List, Any


def compute_tags(records: Iterable[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    """Lightweight tag computation reusing heuristic rules.

    Input records should contain at least {id, conversation_id, content_text}.
    Output records include {id, conversation_id, tags:[{tag, confidence, source}]}
    """
    from ...ingest.tagger import apply_tags  # local reuse to avoid duplication

    for rec in apply_tags(records):
        yield {
            "id": rec.get("id"),
            "conversation_id": rec.get("conversation_id"),
            "tags": rec.get("tags") or [],
        }


