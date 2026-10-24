from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from .load_raw import load_export

# Stable namespace for normalized message IDs
NAMESPACE_NEUROTRACE = uuid.UUID("00000000-0000-0000-0000-00000000abcd")

ROLE_ORDER = {
    "system": 0,
    "tool": 1,
    "assistant": 2,
    "user": 3,
}


def _detect_structure(raw: Dict[str, Any]) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        return raw
    if "conversations" in raw and isinstance(raw["conversations"], list):
        return raw["conversations"]
    if "items" in raw and isinstance(raw["items"], list):
        return raw["items"]
    if "threads" in raw and isinstance(raw["threads"], list):
        return raw["threads"]
    if isinstance(raw, dict) and isinstance(raw.get("messages"), list):
        return [raw]
    if isinstance(raw, dict) and "mapping" in raw:
        return [raw]
    return []


def _extract_content_text(message: Dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, dict):
        parts = content.get("parts")
        if isinstance(parts, list):
            texts = [p for p in parts if isinstance(p, str)]
            return "\n".join(texts)
        text = content.get("text")
        if isinstance(text, str):
            return text
    # Some exports store text under 'body' or top-level
    for key in ("body", "text"):
        val = message.get(key)
        if isinstance(val, str):
            return val
    return ""


def _extract_attachments(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    attachments: List[Dict[str, Any]] = []
    md = message.get("metadata")
    if isinstance(md, dict) and md.get("attachments"):
        a = md.get("attachments")
        if isinstance(a, list):
            for item in a:
                if isinstance(item, dict):
                    attachments.append(item)
    return attachments


def _compute_node_path(mapping: Dict[str, Any], node_id: str) -> str:
    path_ids: List[str] = []
    current = node_id
    visited = set()
    while current and current not in visited:
        visited.add(current)
        path_ids.append(current)
        node = mapping.get(current)
        if not isinstance(node, dict):
            break
        # Prefer message.parent when present; some nodes store parent in node['parent']
        parent = None
        msg = node.get("message")
        if isinstance(msg, dict):
            parent = msg.get("parent")
        if parent is None:
            parent = node.get("parent")
        if not parent or parent not in mapping:
            break
        current = parent  # type: ignore[assignment]
    path_ids.reverse()
    return "/".join(path_ids)


def _normalized_id(raw_id: str, title: Optional[str], node_path: str) -> str:
    base = f"{raw_id}|{title or ''}|{node_path}"
    return str(uuid.uuid5(NAMESPACE_NEUROTRACE, base))


def _conversation_identifier(conv: Dict[str, Any], fallback_index: int) -> str:
    for key in ("conversation_id", "id", "thread_id", "slug", "name"):
        value = conv.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value)
    return f"_thread_{fallback_index:04d}"


def _resolve_gizmo_id(conv: Dict[str, Any]) -> str:
    for key in ("gizmo_id", "project_id", "app_id"):
        value = conv.get(key)
        if isinstance(value, (str, int)) and str(value).strip():
            return str(value)
    return "_orphan"


def _normalize_linear_messages(
    conv: Dict[str, Any],
    index: int,
    duplicates_tracker: Dict[str, List[str]],
) -> Iterator[Dict[str, Any]]:
    messages = conv.get("messages")
    if not isinstance(messages, list):
        return

    title = conv.get("title") if isinstance(conv.get("title"), str) else None
    conv_id = _conversation_identifier(conv, index)
    gizmo_id = _resolve_gizmo_id(conv)

    filtered: List[Tuple[int, Dict[str, Any]]] = [
        (pos, msg) for pos, msg in enumerate(messages) if isinstance(msg, dict)
    ]
    if not filtered:
        return

    def _order_key(entry: Tuple[int, Dict[str, Any]]) -> Tuple[Any, int, str]:
        pos, msg = entry
        ts = msg.get("create_time")
        if ts is None:
            ts = msg.get("created_at")
        return (
            ts if ts is not None else float("inf"),
            pos,
            str(msg.get("id") or f"{conv_id}:{pos}")
        )

    filtered.sort(key=_order_key)

    previous_norm: Optional[str] = None
    for order, msg in filtered:
        raw_id = msg.get("id") or f"{conv_id}:{order}"
        raw_id = str(raw_id)
        node_path = f"seq/{order:06d}"
        norm_id = _normalized_id(raw_id, title if isinstance(title, str) else None, node_path)
        duplicates_tracker.setdefault(raw_id, []).append(norm_id)

        created_at = msg.get("create_time")
        if created_at is None:
            created_at = msg.get("created_at")

        attachments = _extract_attachments(msg)
        content = msg.get("content") if isinstance(msg.get("content"), dict) else None
        content_type = msg.get("content_type")
        if not isinstance(content_type, str) and isinstance(content, dict):
            inferred = content.get("content_type") or content.get("type")
            if isinstance(inferred, str):
                content_type = inferred

        content_text = _extract_content_text(msg)

        record = {
            "id": norm_id,
            "raw_id": raw_id,
            "conversation_id": conv_id,
            "gizmo_id": gizmo_id,
            "parent_id": previous_norm,
            "role": str(msg.get("role") or "assistant"),
            "created_at": created_at,
            "content_text": content_text,
            "content_type": content_type or "text",
            "attachments_json": json.dumps(attachments, ensure_ascii=False),
            "meta_json": json.dumps({"source": "messages", "index": order}, ensure_ascii=False),
        }
        yield record
        previous_norm = norm_id


def _write_duplicates_manifest(dupes: Dict[str, List[str]]) -> None:
    out_dir = Path("outputs/validation")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "duplicates": [
            {"raw_id": rid, "occurrences": occ}
            for rid, occ in sorted(dupes.items(), key=lambda kv: kv[0])
            if len(occ) > 1
        ]
    }
    with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def normalize_messages(raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Yield normalized message records.

    Fields: id, raw_id, conversation_id, parent_id, role, created_at,
    content_text, content_type, attachments_json, meta_json.

    Strategy A tie-breaks on created_at ties: role order, shorter content_text,
    then lexicographic id.
    """
    conversations = _detect_structure(raw)

    duplicates_tracker: Dict[str, List[str]] = {}

    for idx, conv in enumerate(conversations):
        if not isinstance(conv, dict):
            continue

        mapping = conv.get("mapping") if isinstance(conv, dict) else None
        if not isinstance(mapping, dict):
            if isinstance(conv.get("messages"), list):
                yield from _normalize_linear_messages(conv, idx, duplicates_tracker)
            continue

        title = conv.get("title") if isinstance(conv, dict) else None
        # Build list of candidate nodes
        items: List[Tuple[str, Dict[str, Any]]] = []
        for node_key, node in mapping.items():
            if not isinstance(node, dict):
                continue
            msg = node.get("message")
            if not isinstance(msg, dict):
                continue
            items.append((node_key, msg))

        # Sort by Strategy A within this conversation
        sortable: List[Tuple[Tuple[Any, int, int, str], Tuple[str, Dict[str, Any]]]] = []
        for node_id, msg in items:
            created_at = msg.get("create_time")
            role = None
            author = msg.get("author")
            if isinstance(author, dict):
                role = author.get("role")
            if not isinstance(role, str):
                role = msg.get("role") if isinstance(msg.get("role"), str) else "assistant"
            content_text = _extract_content_text(msg)
            # For sorting: None timestamps treated as very large to keep after known ones
            created_sort = (created_at if created_at is not None else float("inf"))
            role_rank = ROLE_ORDER.get(role, 99)
            sortable.append(((created_sort, role_rank, len(content_text), node_id), (node_id, msg)))
        sortable.sort(key=lambda t: t[0])

        # Emit records with normalized IDs and parent recovery
        gizmo_id = "_orphan"
        if isinstance(conv, dict):
            raw_gizmo = conv.get("gizmo_id")
            if raw_gizmo:
                gizmo_id = raw_gizmo

        node_to_norm: Dict[str, str] = {}
        raw_to_norm: Dict[str, str] = {}
        normalized_items: List[Tuple[str, Dict[str, Any], str, str, str]] = []

        for _, (node_id, msg) in sortable:
            raw_id = msg.get("id") or node_id
            if not isinstance(raw_id, str):
                raw_id = str(raw_id)
            node_path = _compute_node_path(mapping, node_id)
            # Same fallback as the linear-messages path, so a conversation without
            # an id still forms a session instead of being dropped.
            conv_id = msg.get("conversation_id") or _conversation_identifier(conv, idx)
            norm_id = _normalized_id(raw_id, title if isinstance(title, str) else None, node_path)

            node_to_norm[node_id] = norm_id
            raw_to_norm[raw_id] = norm_id
            normalized_items.append((node_id, msg, raw_id, norm_id, conv_id))

            # Track duplicates
            duplicates_tracker.setdefault(raw_id, []).append(norm_id)

        for node_id, msg, raw_id, norm_id, conv_id in normalized_items:
            parent_candidates: List[str] = []
            parent_from_msg = msg.get("parent")
            if isinstance(parent_from_msg, str) and parent_from_msg:
                parent_candidates.append(parent_from_msg)
            node_entry = mapping.get(node_id)
            if isinstance(node_entry, dict):
                parent_from_node = node_entry.get("parent")
                if isinstance(parent_from_node, str) and parent_from_node:
                    parent_candidates.append(parent_from_node)

            parent_id = None
            for candidate in parent_candidates:
                parent_id = node_to_norm.get(candidate) or raw_to_norm.get(candidate)
                if parent_id:
                    break

            attachments = _extract_attachments(msg)
            content_type = msg.get("content", {}).get("content_type") if isinstance(msg.get("content"), dict) else None
            content_text = _extract_content_text(msg)
            record = {
                "id": norm_id,
                "raw_id": raw_id,
                "conversation_id": conv_id,
                "gizmo_id": gizmo_id,
                "parent_id": parent_id,
                "role": (msg.get("author", {}) or {}).get("role") if isinstance(msg.get("author"), dict) else msg.get("role"),
                "created_at": msg.get("create_time"),
                "content_text": content_text,
                "content_type": content_type or "text",
                "attachments_json": json.dumps(attachments, ensure_ascii=False),
                "meta_json": json.dumps({"node_id": node_id}, ensure_ascii=False),
            }
            yield record

    # After processing all conversations, write duplicates manifest
    _write_duplicates_manifest(duplicates_tracker)


def group_sessions_from_records(records: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """Group normalized message records into per-session dicts.

    Input records are expected to include at least: id, conversation_id,
    content_text, role, and created_at. Output preserves deterministic ordering
    by sorting within each session by (created_at, id).
    """
    by_sid: Dict[str, List[Dict[str, Any]]] = {}
    for rec in records:
        sid = str(rec.get("conversation_id") or "").strip()
        if not sid:
            continue
        by_sid.setdefault(sid, []).append(rec)

    sessions: List[Dict[str, Any]] = []
    message_total = 0
    for sid in sorted(by_sid.keys()):
        recs = by_sid[sid]
        recs.sort(
            key=lambda r: (
                r.get("created_at") if r.get("created_at") is not None else float("inf"),
                str(r.get("id") or ""),
            )
        )
        gizmo_id = recs[0].get("gizmo_id") if recs else "_orphan"
        if not gizmo_id:
            gizmo_id = "_orphan"
        messages: List[Dict[str, Any]] = []
        for idx, r in enumerate(recs):
            messages.append(
                {
                    "id": str(r.get("id") or f"{sid}:{idx}"),
                    "role": str(r.get("role") or ""),
                    "content_text": str(r.get("content_text") or ""),
                    "create_time": r.get("created_at"),
                }
            )
        message_total += len(messages)
        sessions.append({"id": sid, "gizmo_id": gizmo_id, "messages": messages})
    return sessions, message_total
