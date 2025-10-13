from __future__ import annotations

from pathlib import Path
import sys


def _add_src_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_src_to_path()

from neurotrace.ingest.privacy import pseudonymize, redact  # noqa: E402
from neurotrace.ingest.tagger import apply_tags  # noqa: E402


def test_privacy_pseudonymize_and_redact():
    rec = {
        "content_text": "Contact me at alice@example.com or +1-555-123-4567 and see https://example.com",
    }
    p = list(pseudonymize([rec]))[0]
    r = list(redact([rec]))[0]
    assert p["content_text"] != rec["content_text"]
    assert "[REDACTED]" in r["content_text"]


def test_tagger_assigns_priority_tags():
    recs = [{"content_text": "Plan next step and remember this."}]
    tagged = list(apply_tags(recs))[0]
    tags = [t["tag"] for t in tagged.get("tags", [])]
    # Priority includes planning and memory
    assert "planning" in tags or "memory" in tags
