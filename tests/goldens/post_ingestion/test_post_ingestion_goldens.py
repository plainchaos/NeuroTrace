from __future__ import annotations

import json
from pathlib import Path
import sys

from neurotrace.eval.quality_gates import hash_json


def _add_src_to_path() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


_add_src_to_path()

from neurotrace.ingest.load_raw import load_export  # noqa: E402
from neurotrace.ingest.normalize import normalize_messages  # noqa: E402
from neurotrace.ingest.privacy import pseudonymize  # noqa: E402
from neurotrace.ingest.tagger import apply_tags  # noqa: E402
from neurotrace.ingest.metrics_pass import compute_session_metrics  # noqa: E402
from neurotrace.ingest.writer_sqlite import write_sqlite  # noqa: E402
from neurotrace.query.storage import open_db, fetch_distinct_conversations  # noqa: E402
from neurotrace.query.summaries import session_summary  # noqa: E402
from neurotrace.analytics.graphs import make_tree  # noqa: E402
from neurotrace.visuals.api_specs import vega_zone_mix, vega_session_overview, vega_depth_dist, vega_transitions  # noqa: E402


def _build_db_from_seed(tmp_path: Path) -> str:
    repo_root = Path(__file__).resolve().parents[3]
    seed = repo_root / "tests/fixtures/seed/canonical_export_snippet.json"
    raw = load_export(str(seed))
    records = list(normalize_messages(raw))
    records = list(pseudonymize(records))
    records = list(apply_tags(records))
    metrics = compute_session_metrics(records)
    db = tmp_path / "golden.db"
    write_sqlite(records, metrics, str(db))
    return str(db)


def _read_golden(name: str) -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    p = repo_root / f"tests/goldens/post_ingestion/{name}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def test_summary_tree_visuals_match_goldens(tmp_path):
    db_path = _build_db_from_seed(tmp_path)
    with open_db(db_path) as conn:
        sessions = list(fetch_distinct_conversations(conn))
        sid = sessions[0] if sessions else ""
        summary = session_summary(conn, sid)
        tree = make_tree(conn, sid)
        overview_spec = vega_session_overview(summary)
        zone_mix_spec = vega_zone_mix(summary)
        depth_spec = vega_depth_dist(summary)
        transitions_spec = vega_transitions(summary)

    # Compute hashes
    got_hashes = {
        "summary": hash_json(summary),
        "tree": hash_json(tree),
        "overview": hash_json(overview_spec),
        "zone_mix": hash_json(zone_mix_spec),
        "depth_dist": hash_json(depth_spec),
        "transitions": hash_json(transitions_spec),
    }

    # Golden payloads
    want = {
        "summary": _read_golden("summary"),
        "tree": _read_golden("tree"),
        "overview": _read_golden("overview"),
        "zone_mix": _read_golden("zone_mix"),
        "depth_dist": _read_golden("depth_dist"),
        "transitions": _read_golden("transitions"),
    }
    want_hashes = {k: hash_json(v) for k, v in want.items()}

    assert got_hashes == want_hashes


