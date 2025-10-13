from __future__ import annotations

from neurotrace.query.filters import by_session, since


def test_by_session_predicate():
    where, params = by_session("abc")
    assert where == "conversation_id = ?"
    assert params == ("abc",)


def test_since_predicate():
    where, params = since("2024-01-01T00:00:00Z")
    assert where == "created_at >= ?"
    assert params == ("2024-01-01T00:00:00Z",)



