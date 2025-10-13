from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple


def _tokenize(text: str) -> List[str]:
    return [t for t in text.lower().split() if t.isascii()]


def compute_semantic_index_and_links(
    sessions: Iterable[Dict[str, Any]], *, max_keywords_per_message: int = 5
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Lightweight, deterministic semantic index and links.

    - Index: [{message_id, session_id, keywords: [..]}]
    - Links: [{from, to, kind: "sequence"}] (adjacent messages within a session)
    """
    index: List[Dict[str, Any]] = []
    links: List[Dict[str, Any]] = []

    for sess in sessions:
        sid = str(sess.get("id") or sess.get("session_id") or "")
        messages: List[Dict[str, Any]] = list(sess.get("messages", []))
        # Deterministic order: preserve given order; fallback to id sort if needed
        if messages and "order" in messages[0]:
            messages.sort(key=lambda m: (m.get("order"), m.get("id", "")))
        elif messages and "create_time" in messages[0]:
            messages.sort(key=lambda m: (m.get("create_time") or 0.0, m.get("id", "")))
        else:
            messages.sort(key=lambda m: m.get("id", ""))

        for i, m in enumerate(messages):
            mid = str(m.get("id") or f"{sid}:{i}")
            text = str(m.get("content") or m.get("content_text") or "")
            toks = _tokenize(text)
            # Deterministic: sort tokens, deduplicate, take first N
            uniq = []
            for t in sorted(toks):
                if t not in uniq:
                    uniq.append(t)
            index.append({
                "message_id": mid,
                "session_id": sid,
                "keywords": uniq[:max_keywords_per_message],
            })
            if i > 0:
                prev = messages[i - 1]
                links.append({
                    "from": str(prev.get("id") or f"{sid}:{i-1}"),
                    "to": mid,
                    "kind": "sequence",
                })

    # Final deterministic ordering
    index.sort(key=lambda r: (r["session_id"], r["message_id"]))
    links.sort(key=lambda r: (r["from"], r["to"]))
    return index, links


