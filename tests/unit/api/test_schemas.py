from __future__ import annotations

from neurotrace.api.schemas import HealthResponse, SessionSummary, TreeNode


def test_health_response_model():
    obj = HealthResponse(status="ok", schema_hash="abc", golden_hash=None)
    data = obj.model_dump()
    assert data["status"] == "ok"


def test_session_summary_model():
    ss = SessionSummary(session_id="s1", message_count=3, start_ts=1.0, end_ts=2.0)
    data = ss.model_dump()
    assert data["session_id"] == "s1"
    assert data["message_count"] == 3


def test_tree_node_forward_refs():
    node = TreeNode(id="root", children=[])
    assert node.id == "root"



