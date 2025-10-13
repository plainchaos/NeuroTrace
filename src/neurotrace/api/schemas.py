from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class HealthResponse(BaseModel):
    """Health payload including determinism hashes and version."""

    status: Optional[str] = None
    schema_hash: Optional[str] = None
    golden_hash: Optional[str] = None
    version: Optional[str] = None


class SessionSummary(BaseModel):
    session_id: str
    message_count: int
    start_ts: Optional[float]
    end_ts: Optional[float]


class TreeNode(BaseModel):
    id: str
    children: List["TreeNode"] = Field(default_factory=list)  # type: ignore[misc]


class SessionItem(BaseModel):
    """Lightweight session row for listings.

    Matches { id, started_at, message_count } with ISO8601 timestamp for started_at.
    """

    id: str
    started_at: Optional[str] = None
    message_count: int


TreeNode.update_forward_refs()


