from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, List

_PRIORITY = ["memory", "planning", "feedback", "reflection", "response"]

_KEYWORDS = {
    "memory": ["remember", "note", "recall"],
    "planning": ["plan", "next step", "roadmap"],
    "feedback": ["review", "feedback", "critique"],
    "reflection": ["reflect", "thinking", "consider"],
}


def _score_tags(text: str) -> List[Dict[str, Any]]:
    text_l = text.lower()
    scores: Dict[str, float] = {k: 0.0 for k in _PRIORITY}
    for tag, words in _KEYWORDS.items():
        for w in words:
            if w in text_l:
                scores[tag] += 1.0
    ranked = [t for t in _PRIORITY if scores.get(t, 0.0) > 0]
    return [{"tag": t, "confidence": min(1.0, scores[t] / 3.0), "source": "heuristic"} for t in ranked]


def apply_tags(records: Iterable[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    for rec in records:
        text = rec.get("content_text")
        tags: List[Dict[str, Any]] = []
        if isinstance(text, str) and text:
            tags = _score_tags(text)
        out = dict(rec)
        out["tags"] = tags
        yield out
