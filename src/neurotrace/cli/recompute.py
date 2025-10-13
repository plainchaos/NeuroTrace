from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer

from neurotrace.storage.raw import RawSource
from neurotrace.storage.derived import DerivedStore
from neurotrace.utils.fs import get_project_root
from neurotrace.utils.manifest import iso_now_utc
from neurotrace.analytics.tagging import compute_tags
from neurotrace.analytics.zone_transitions import compute_zone_mix_and_transitions
from neurotrace.analytics.response_depth import compute_depth_distribution
from neurotrace.analytics.metrics import compute_metrics
from neurotrace.analytics.semantic_memory import compute_semantic_index_and_links
from neurotrace.visuals.api_specs import (
    vega_session_overview,
    vega_zone_mix,
    vega_depth_dist,
    vega_transitions,
)
from neurotrace.ingest.load_raw import load_export
from neurotrace.ingest.normalize import normalize_messages, group_sessions_from_records


app = typer.Typer(name="recompute")


def _default_run_id() -> str:
    # ISO yyyymmddTHHMMSSZ per blueprint for folder naming only
    from datetime import datetime, timezone

    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _resolve_inputs(input_path: str) -> List[Path]:
    p = Path(input_path)
    if p.is_dir():
        return sorted([q for q in p.glob("*.json")])
    if p.is_file():
        return [p]
    return []


def _summarize_payload(payload: Any) -> Tuple[str, List[str]]:
    payload_type = type(payload).__name__
    keys: List[str] = []
    if isinstance(payload, dict):
        keys = sorted(str(k) for k in payload.keys())
    return payload_type, keys


def _load_sessions_and_records_from_input(path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str], Optional[Tuple[str, List[str]]]]:
    files = _resolve_inputs(path)
    input_names = [p.name for p in files]
    normalized_records: List[Dict[str, Any]] = []
    top_summary: Optional[Tuple[str, List[str]]] = None
    for idx, p in enumerate(files):
        raw = load_export(str(p))
        if idx == 0:
            top_summary = _summarize_payload(raw)
        normalized_records.extend(list(normalize_messages(raw)))
    sessions, _ = group_sessions_from_records(normalized_records)
    return sessions, normalized_records, input_names, top_summary


@app.command("tagging")
def recompute_tagging(
    run_id: Optional[str] = typer.Option(None, help="Run ID for derived folder"),
    input: Optional[str] = typer.Option(None, help="Path to export .json or directory of JSON files"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase log detail (-v, -vv)"),
) -> None:
    rid = run_id or _default_run_id()
    store = DerivedStore("tagging")

    # Determine records source
    inputs_meta: Dict[str, Any]
    if input:
        try:
            sessions, normalized_records, input_names, top_summary = _load_sessions_and_records_from_input(input)
        except FileNotFoundError:
            typer.echo(f"ERROR: input not found: {input}"); raise typer.Exit(3)
        if len(sessions) == 0:
            origin = input
            detail = ""
            if top_summary:
                detail = f" (top-level {top_summary[0]} keys={top_summary[1]})"
            accepted = "expected JSON list of sessions, dict with 'conversations'/'items'/'threads', dict with 'messages', or directory of *.json"
            typer.echo(f"ERROR: no conversations detected from {origin}{detail}; {accepted}")
            raise typer.Exit(4)
        records = [
            {"id": r.get("id"), "conversation_id": r.get("conversation_id"), "content_text": r.get("content_text")}
            for r in normalized_records
        ]
        inputs_meta = {"files": input_names}
    else:
        raw = RawSource()
        # For simplicity, iterate sessions and messages from JSON root; expect files named by session id
        records = []  # type: ignore[no-redef]
        for sid in raw.iter_session_ids():
            session = raw.read_session(sid)
            for msg in session.get("messages", []):
                records.append(
                    {
                        "id": msg.get("id") or f"{sid}:{len(records)}",
                        "conversation_id": sid,
                        "content_text": msg.get("content", ""),
                    }
                )
        inputs_meta = {"raw_root": str(raw.json_root.relative_to(get_project_root()))}

    tags = list(compute_tags(records))
    out_path = store.write_json(rid, "tags.json", tags)
    store.finalize_manifest(rid, inputs=inputs_meta, version="mvp1")
    typer.echo(str(out_path))


@app.command("transitions")
def recompute_transitions(
    run_id: Optional[str] = typer.Option(None, help="Run ID for derived folder"),
    input: Optional[str] = typer.Option(None, help="Path to export .json or directory of JSON files"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase log detail (-v, -vv)"),
) -> None:
    rid = run_id or _default_run_id()
    store = DerivedStore("transitions")
    inputs_meta: Dict[str, Any]
    if input:
        try:
            sessions, _records, input_names, top_summary = _load_sessions_and_records_from_input(input)
        except FileNotFoundError:
            typer.echo(f"ERROR: input not found: {input}"); raise typer.Exit(3)
        if len(sessions) == 0:
            origin = input
            detail = ""
            if top_summary:
                detail = f" (top-level {top_summary[0]} keys={top_summary[1]})"
            accepted = "expected JSON list of sessions, dict with 'conversations'/'items'/'threads', dict with 'messages', or directory of *.json"
            typer.echo(f"ERROR: no conversations detected from {origin}{detail}; {accepted}")
            raise typer.Exit(4)
        inputs_meta = {"files": input_names}
    else:
        raw = RawSource()
        sessions = []
        for sid in raw.iter_session_ids():
            sessions.append(raw.read_session(sid))
        inputs_meta = {"raw_root": str(raw.json_root.relative_to(get_project_root()))}

    zone_mix, transitions = compute_zone_mix_and_transitions(sessions)
    store.write_json(rid, "zone_mix.json", zone_mix)
    store.write_json(rid, "transitions.json", transitions)
    store.finalize_manifest(rid, inputs=inputs_meta, version="mvp1")
    typer.echo(str(store.path(rid)))


@app.command("visuals")
def recompute_visuals(run_id: Optional[str] = typer.Option(None, help="Run ID for derived folder")) -> None:
    """Build display-only specs by reading derived analytics outputs.

    Requires that transitions and depth have been recomputed (zone_mix.json, transitions.json, depth_dist.json).
    """
    rid = run_id or _default_run_id()
    store = DerivedStore("visuals")

    # Read analytics outputs from latest run_id if not provided; here we reuse the same rid for simplicity
    derived_root = Path("outputs/derived")
    # Overview requires a per-session summary; for MVP, emit a minimal overview using counts in metrics.json if present
    overview = {"message_count": 0, "start_ts": 0.0, "end_ts": 0.0, "zones": []}
    metrics_path = derived_root / "metrics" / rid / "metrics.json"
    if metrics_path.exists():
        try:
            import json as _json
            m = _json.loads(metrics_path.read_text(encoding="utf-8"))
            overview["message_count"] = int(m.get("messages", 0))
        except Exception:
            pass
    store.write_json(rid, "overview.json", vega_session_overview(overview))

    # Zone mix and transitions specs directly from corresponding analytics outputs
    import json as _json
    zm_path = derived_root / "transitions" / rid / "zone_mix.json"
    tr_path = derived_root / "transitions" / rid / "transitions.json"
    dd_path = derived_root / "depth" / rid / "depth_dist.json"
    if zm_path.exists():
        zone_mix = _json.loads(zm_path.read_text(encoding="utf-8"))
        spec = vega_zone_mix({"zones": zone_mix})
        store.write_json(rid, "zone_mix.json", spec)
    if tr_path.exists():
        transitions = _json.loads(tr_path.read_text(encoding="utf-8"))
        # For transitions spec, we can feed a summary-like shape if needed
        spec = vega_transitions({"transitions": transitions})
        store.write_json(rid, "transitions.json", spec)
    if dd_path.exists():
        depth = _json.loads(dd_path.read_text(encoding="utf-8"))
        spec = vega_depth_dist({"depths": depth})
        store.write_json(rid, "depth_dist.json", spec)

    store.finalize_manifest(rid, inputs={"analytics_run_id": rid}, version="mvp1")
    typer.echo(str(store.path(rid)))


@app.command("metrics")
def recompute_metrics(
    run_id: Optional[str] = typer.Option(None, help="Run ID for derived folder"),
    input: Optional[str] = typer.Option(None, help="Path to export .json or directory of JSON files"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase log detail (-v, -vv)"),
) -> None:
    rid = run_id or _default_run_id()
    store = DerivedStore("metrics")
    inputs_meta: Dict[str, Any]
    if input:
        try:
            sessions, _records, input_names, top_summary = _load_sessions_and_records_from_input(input)
        except FileNotFoundError:
            typer.echo(f"ERROR: input not found: {input}"); raise typer.Exit(3)
        if len(sessions) == 0:
            origin = input
            detail = ""
            if top_summary:
                detail = f" (top-level {top_summary[0]} keys={top_summary[1]})"
            accepted = "expected JSON list of sessions, dict with 'conversations'/'items'/'threads', dict with 'messages', or directory of *.json"
            typer.echo(f"ERROR: no conversations detected from {origin}{detail}; {accepted}")
            raise typer.Exit(4)
        inputs_meta = {"files": input_names}
    else:
        raw = RawSource()
        sessions = []
        for sid in raw.iter_session_ids():
            sessions.append(raw.read_session(sid))
        inputs_meta = {"raw_root": str(raw.json_root.relative_to(get_project_root()))}

    payload = compute_metrics(sessions)
    store.write_json(rid, "metrics.json", payload)
    store.finalize_manifest(rid, inputs=inputs_meta, version="mvp1")
    typer.echo(str(store.path(rid)))


@app.command("semantic-memory")
def recompute_semantic_memory(
    run_id: Optional[str] = typer.Option(None, help="Run ID for derived folder"),
    enable_embeddings: bool = typer.Option(False, help="OFF by default: do not compute heavy embeddings"),
    input: Optional[str] = typer.Option(None, help="Path to export .json or directory of JSON files"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase log detail (-v, -vv)"),
) -> None:
    rid = run_id or _default_run_id()
    store = DerivedStore("analysis")
    inputs_meta: Dict[str, Any]
    if input:
        try:
            sessions, _records, input_names, top_summary = _load_sessions_and_records_from_input(input)
        except FileNotFoundError:
            typer.echo(f"ERROR: input not found: {input}"); raise typer.Exit(3)
        if len(sessions) == 0:
            origin = input
            detail = ""
            if top_summary:
                detail = f" (top-level {top_summary[0]} keys={top_summary[1]})"
            accepted = "expected JSON list of sessions, dict with 'conversations'/'items'/'threads', dict with 'messages', or directory of *.json"
            typer.echo(f"ERROR: no conversations detected from {origin}{detail}; {accepted}")
            raise typer.Exit(4)
        inputs_meta = {"files": input_names}
    else:
        raw = RawSource()
        sessions = []
        for sid in raw.iter_session_ids():
            sessions.append(raw.read_session(sid))
        inputs_meta = {"raw_root": str(raw.json_root.relative_to(get_project_root()))}

    index, links = compute_semantic_index_and_links(sessions)
    store.write_json(rid, "semantic_index.json", index)
    store.write_json(rid, "semantic_links.json", links)
    # Heavy embedding disabled by default; if enabled, would write additional files
    store.finalize_manifest(rid, inputs=inputs_meta, version="mvp1")
    typer.echo(str(store.path(rid)))


@app.command("depth")
def recompute_depth(
    run_id: Optional[str] = typer.Option(None, help="Run ID for derived folder"),
    input: Optional[str] = typer.Option(None, help="Path to export .json or directory of JSON files"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase log detail (-v, -vv)"),
) -> None:
    rid = run_id or _default_run_id()
    store = DerivedStore("depth")
    inputs_meta: Dict[str, Any]
    if input:
        try:
            sessions, _records, input_names, top_summary = _load_sessions_and_records_from_input(input)
        except FileNotFoundError:
            typer.echo(f"ERROR: input not found: {input}"); raise typer.Exit(3)
        if len(sessions) == 0:
            origin = input
            detail = ""
            if top_summary:
                detail = f" (top-level {top_summary[0]} keys={top_summary[1]})"
            accepted = "expected JSON list of sessions, dict with 'conversations'/'items'/'threads', dict with 'messages', or directory of *.json"
            typer.echo(f"ERROR: no conversations detected from {origin}{detail}; {accepted}")
            raise typer.Exit(4)
        inputs_meta = {"files": input_names}
    else:
        raw = RawSource()
        sessions = []
        for sid in raw.iter_session_ids():
            sessions.append(raw.read_session(sid))
        inputs_meta = {"raw_root": str(raw.json_root.relative_to(get_project_root()))}

    depth_dist = compute_depth_distribution(sessions)
    store.write_json(rid, "depth_dist.json", depth_dist)
    store.finalize_manifest(rid, inputs=inputs_meta, version="mvp1")
    typer.echo(str(store.path(rid)))


if __name__ == "__main__":
    app()

