from __future__ import annotations

from typing import Any, Dict, List, Tuple


def _detect_structure(raw: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    # Support wrappers: {conversations: [...]}, or direct list under 'items'
    if "conversations" in raw and isinstance(raw["conversations"], list):
        return ("conversations", raw["conversations"])  # type: ignore[return-value]
    # Some exports embed under 'items'
    if "items" in raw and isinstance(raw["items"], list):
        return ("items", raw["items"])  # type: ignore[return-value]
    # If raw looks like a single conversation dict wrapped, normalize
    if isinstance(raw, dict) and "mapping" in raw:
        return ("single", [raw])
    # Fallback: empty list
    return ("unknown", [])


def validate_raw_export(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Return a report dict with counts, structural anomalies, orphan checks, attachment shapes.

    The function is non-intrusive and avoids mutating the input. It copes with multiple
    known shapes of ChatGPT exports and degrades gracefully.
    """
    report: Dict[str, Any] = {
        "shape": None,
        "num_conversations": 0,
        "num_messages_total": 0,
        "orphans": 0,
        "attachments_summary": {
            "conversations_with_attachments": 0,
            "attachments_count": 0,
        },
        "anomalies": [],  # strings suitable for human logs
    }

    shape, conversations = _detect_structure(raw)
    report["shape"] = shape
    report["num_conversations"] = len(conversations)

    total_messages = 0
    orphans = 0
    conv_with_attachments = 0
    attachments_count = 0

    for conv in conversations:
        mapping = conv.get("mapping") if isinstance(conv, dict) else None
        if not isinstance(mapping, dict):
            report["anomalies"].append("conversation_missing_mapping")
            continue
        # Count messages by mapping entries that have 'message'
        for node_id, node in mapping.items():
            if not isinstance(node, dict):
                report["anomalies"].append("node_not_dict")
                continue
            msg = node.get("message")
            if msg is None:
                continue
            total_messages += 1
            parent = msg.get("parent") if isinstance(msg, dict) else None
            if parent and parent not in mapping:
                orphans += 1
            # attachments may live under metadata or content parts
            attachments = []
            if isinstance(msg, dict):
                md = msg.get("metadata")
                if isinstance(md, dict) and md.get("attachments"):
                    a = md.get("attachments")
                    if isinstance(a, list):
                        attachments.extend(a)
            if attachments:
                conv_with_attachments += 1
                attachments_count += len(attachments)

    report["num_messages_total"] = total_messages
    report["orphans"] = orphans
    report["attachments_summary"]["conversations_with_attachments"] = conv_with_attachments
    report["attachments_summary"]["attachments_count"] = attachments_count

    return report
