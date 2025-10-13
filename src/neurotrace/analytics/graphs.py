from __future__ import annotations

import sqlite3
from typing import Any, Dict, List


def make_tree(conn: sqlite3.Connection, session_id: str) -> Dict[str, Any]:
    """Return a simple tree JSON (acyclic) for a session.

    Enforces single-parent and builds a node map with children lists.
    """
    cur = conn.execute(
        "SELECT id, parent_id, role, create_time FROM messages WHERE conversation_id = ? ORDER BY create_time, id",
        (session_id,),
    )
    nodes: Dict[str, Dict[str, Any]] = {}
    children: Dict[str, List[str]] = {}
    for mid, parent_id, role, ts in cur.fetchall():
        nodes[mid] = {"id": mid, "parent_id": parent_id, "role": role, "ts": ts}
        children.setdefault(mid, [])
        if parent_id:
            children.setdefault(parent_id, []).append(mid)

    # find roots (no parent or missing parent)
    roots = [nid for nid, n in nodes.items() if not n["parent_id"] or n["parent_id"] not in nodes]

    def build(nid: str) -> Dict[str, Any]:
        return {"id": nid, "children": [build(cid) for cid in children.get(nid, [])]}

    return {"session_id": session_id, "roots": [build(r) for r in roots]}


