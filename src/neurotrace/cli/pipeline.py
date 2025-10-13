from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

import typer

from ..utils.log import get_logger, task_fail, task_ok, task_start
from ..config import RUN_ID_FORMAT
from ..storage.derived import DerivedStore
from ..analytics.zone_transitions import compute_zone_mix_and_transitions
from ..analytics.response_depth import compute_depth_distribution
from ..analytics.metrics import compute_metrics
from ..analytics.semantic_memory import compute_semantic_index_and_links
from ..visuals.api_specs import vega_session_overview, vega_zone_mix, vega_depth_dist, vega_transitions
from ..ingest.load_raw import load_export
from ..ingest.normalize import normalize_messages, group_sessions_from_records
from ..ingest.privacy import pseudonymize, redact
from ..ingest.tagger import apply_tags
from ..ingest.metrics_pass import compute_session_metrics as compute_session_metrics_pass
from ..ingest.writer_sqlite import write_sqlite


app = typer.Typer(add_completion=False)


def _gen_run_id() -> str:
    return datetime.now(tz=timezone.utc).strftime(RUN_ID_FORMAT)


def _resolve_inputs(input_path: str) -> list[Path]:
    p = Path(input_path)
    if p.is_dir():
        files = sorted([q for q in p.glob("*.json")])
        return files
    if p.is_file():
        return [p]
    return []


def _summarize_payload(payload: Any) -> Tuple[str, List[str]]:
    payload_type = type(payload).__name__
    keys: List[str] = []
    if isinstance(payload, dict):
        keys = sorted(str(k) for k in payload.keys())
    return payload_type, keys


# sessions grouping is provided by ingest.normalize.group_sessions_from_records


def run_pipeline_orchestrated(
    input: str = typer.Option(..., "--input", help="Raw JSON file or directory"),
    db: Optional[str] = typer.Option(None, "--db", help="Path to create SQLite mirror (optional)"),
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Run ID for derived folders"),
    no_visuals: bool = typer.Option(False, "--no-visuals", help="Skip building visual specs"),
    semantic_memory: bool = typer.Option(True, "--semantic-memory/--no-semantic-memory", help="Compute semantic memory index and links"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing derived folders for this run_id"),
    privacy: str = typer.Option("pseudonymize", "--privacy", help="pseudonymize|redact|none"),
    verbosity: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase log detail (-v, -vv)"),
) -> None:
    """One-shot end-to-end run: ingest → DB mirror → analytics → visuals → aggregator."""
    log = get_logger("neurotrace.pipeline")

    rid = run_id or _gen_run_id()
    input_paths = _resolve_inputs(input)
    if not input_paths:
        task_fail(log, "inputs", "no JSON files found")
        raise typer.Exit(3)

    input_names = [p.name for p in input_paths]
    derived = {
        "tagging": DerivedStore("tagging"),
        "transitions": DerivedStore("transitions"),
        "depth": DerivedStore("depth"),
        "metrics": DerivedStore("metrics"),
        "analysis": DerivedStore("analysis"),
        "visuals": DerivedStore("visuals"),
        "aggregate": DerivedStore("aggregate"),
    }
    prepared: Dict[str, bool] = {}

    def ensure_domain(name: str) -> None:
        if prepared.get(name):
            return
        store = derived[name]
        base = store.path(rid)
        existing = [p for p in base.iterdir()]
        if existing:
            if not force:
                task_fail(
                    log,
                    "preflight",
                    f"run_id={rid} already has artifacts under outputs/derived/{name}; use --force to overwrite",
                )
                raise typer.Exit(8)
            shutil.rmtree(base)
            base.mkdir(parents=True, exist_ok=True)
        prepared[name] = True

    durations: Dict[str, float] = {}
    log.info(f"[pipeline] starting — run_id={rid}")

    tagged_records: List[Dict[str, Any]] = []
    sessions: List[Dict[str, Any]] = []
    session_metrics: Dict[str, Any] = {}
    zone_mix: List[Dict[str, Any]] = []
    transitions: List[Dict[str, Any]] = []
    depth_dist: List[Dict[str, Any]] = []
    metrics_summary: Dict[str, Any] = {}
    message_total = 0
    session_count = 0
    top_summary: Optional[Tuple[str, List[str]]] = None

    try:
        t0 = perf_counter()
        task_start(log, "ingest", f"files={len(input_paths)}")
        normalized_records: List[Dict[str, Any]] = []
        for idx, path_obj in enumerate(input_paths):
            raw_payload = load_export(str(path_obj))
            if idx == 0:
                top_summary = _summarize_payload(raw_payload)
            normalized_records.extend(list(normalize_messages(raw_payload)))

        normalized_count = len(normalized_records)
        if normalized_count == 0:
            origin = input_names[0] if len(input_names) == 1 else "provided inputs"
            detail = ""
            if top_summary:
                detail = f" (top-level {top_summary[0]} keys={top_summary[1]})"
            accepted_shapes = "expected JSON list of sessions, dict with 'conversations'/'items'/'threads', dict with 'messages', or directory of *.json"
            task_fail(
                log,
                "ingest",
                f"no conversations detected in {origin}{detail}; {accepted_shapes}",
            )
            raise typer.Exit(4)

        privacy_mode = privacy.lower().strip()
        if privacy_mode not in {"pseudonymize", "redact", "none"}:
            task_fail(log, "ingest", f"invalid privacy mode: {privacy}")
            raise typer.Exit(3)

        if privacy_mode == "redact":
            sanitized_iter = redact(normalized_records)
        elif privacy_mode == "pseudonymize":
            sanitized_iter = pseudonymize(normalized_records)
        else:
            sanitized_iter = (dict(rec) for rec in normalized_records)

        sanitized_records = [dict(rec) for rec in sanitized_iter]
        tagged_records = [dict(rec) for rec in apply_tags(sanitized_records)]
        for rec in tagged_records:
            rec.setdefault("tags", [])

        sessions, message_total = group_sessions_from_records(tagged_records)
        session_count = len(sessions)
        if session_count == 0:
            origin = input_names[0] if len(input_names) == 1 else "provided inputs"
            detail = ""
            if top_summary:
                detail = f" (top-level {top_summary[0]} keys={top_summary[1]})"
            accepted = "expected dict with 'conversations'/'threads' containing ChatGPT mappings or a dict/list with 'messages' arrays"
            task_fail(
                log,
                "ingest",
                f"no supported sessions found in {origin}{detail}; {accepted}",
            )
            raise typer.Exit(4)

        if verbosity > 0 and top_summary:
            log.info(f"[ingest] source type={top_summary[0]} keys={top_summary[1]}")
        if verbosity > 0:
            log.info(
                f"[ingest] normalized_records={normalized_count} sessions={session_count} messages={message_total}"
            )
            log.info(f"[ingest] resolved run_id={rid}")

        session_metrics = compute_session_metrics_pass(tagged_records)

        durations["ingest"] = perf_counter() - t0
        task_ok(log, "ingest", durations["ingest"], f"sessions={session_count}")
    except typer.Exit:
        raise
    except Exception as exc:
        task_fail(log, "ingest", str(exc))
        raise typer.Exit(4)

    # Optional SQLite mirror
    if db:
        try:
            t0 = perf_counter()
            task_start(log, "mirror-db", f"path={db}")
            db_path = Path(db)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            write_sqlite(tagged_records, session_metrics, str(db_path))
            counts = {}
            with sqlite3.connect(str(db_path)) as conn:
                for table in ("messages", "message_contents"):
                    cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cur.fetchone()[0]
            durations["mirror-db"] = perf_counter() - t0
            task_ok(
                log,
                "mirror-db",
                durations["mirror-db"],
                f"messages={counts.get('messages', 0)} contents={counts.get('message_contents', 0)}",
            )
        except Exception as exc:
            task_fail(log, "mirror-db", str(exc))
            raise typer.Exit(5)

    # Tagging artifacts
    try:
        t0 = perf_counter()
        task_start(log, "tagging")
        ensure_domain("tagging")
        tag_payload = [
            {
                "id": rec.get("id"),
                "conversation_id": rec.get("conversation_id"),
                "tags": rec.get("tags", []),
            }
            for rec in tagged_records
        ]
        store = derived["tagging"]
        store.write_json(rid, "tags.json", tag_payload)
        store.finalize_manifest(rid, inputs={"files": input_names})
        durations["tagging"] = perf_counter() - t0
        task_ok(log, "tagging", durations["tagging"], f"records={len(tag_payload)}")
    except Exception as exc:
        task_fail(log, "tagging", str(exc))
        raise typer.Exit(6)

    # Transitions
    try:
        t0 = perf_counter()
        task_start(log, "transitions")
        zone_mix, transitions = compute_zone_mix_and_transitions(sessions)
        ensure_domain("transitions")
        store = derived["transitions"]
        store.write_json(rid, "zone_mix.json", zone_mix)
        store.write_json(rid, "transitions.json", transitions)
        store.finalize_manifest(rid, inputs={"files": input_names})
        durations["transitions"] = perf_counter() - t0
        task_ok(log, "transitions", durations["transitions"], f"zones={len(zone_mix)}")
    except Exception as exc:
        task_fail(log, "transitions", str(exc))
        raise typer.Exit(6)

    # Depth distribution
    try:
        t0 = perf_counter()
        task_start(log, "depth")
        depth_dist = compute_depth_distribution(sessions)
        ensure_domain("depth")
        store = derived["depth"]
        store.write_json(rid, "depth_dist.json", depth_dist)
        store.finalize_manifest(rid, inputs={"files": input_names})
        durations["depth"] = perf_counter() - t0
        task_ok(log, "depth", durations["depth"], f"bins={len(depth_dist)}")
    except Exception as exc:
        task_fail(log, "depth", str(exc))
        raise typer.Exit(6)

    # Metrics payload (JSON is canonical)
    try:
        t0 = perf_counter()
        task_start(log, "metrics")
        ensure_domain("metrics")
        metrics_summary = compute_metrics(sessions)
        metrics_payload = {
            "summary": {
                "sessions": session_count,
                "messages": int(metrics_summary.get("messages") or message_total),
            },
            "sessions": session_metrics,
        }
        store = derived["metrics"]
        store.write_json(rid, "metrics.json", metrics_payload)
        store.finalize_manifest(rid, inputs={"files": input_names})
        durations["metrics"] = perf_counter() - t0
        task_ok(log, "metrics", durations["metrics"], f"sessions={session_count}")
    except Exception as exc:
        task_fail(log, "metrics", str(exc))
        raise typer.Exit(6)

    # Optional semantic memory domain
    if semantic_memory:
        try:
            t0 = perf_counter()
            task_start(log, "semantic-memory")
            ensure_domain("analysis")
            index, links = compute_semantic_index_and_links(sessions)
            store = derived["analysis"]
            store.write_json(rid, "semantic_index.json", index)
            store.write_json(rid, "semantic_links.json", links)
            store.finalize_manifest(rid, inputs={"files": input_names, "semantic_memory": True})
            durations["semantic_memory"] = perf_counter() - t0
            task_ok(log, "semantic-memory", durations["semantic_memory"], f"records={len(index)}")
        except Exception as exc:
            task_fail(log, "semantic-memory", str(exc))
            raise typer.Exit(6)

    # Visuals domain (deterministic Vega specs)
    if not no_visuals:
        try:
            t0 = perf_counter()
            task_start(log, "visuals")
            ensure_domain("visuals")
            # Compute overview timings
            timestamps = [
                msg.get("create_time")
                for session in sessions
                for msg in session.get("messages", [])
                if msg.get("create_time") is not None
            ]
            start_ts = min(timestamps) if timestamps else 0.0
            end_ts = max(timestamps) if timestamps else 0.0
            overview_spec = vega_session_overview(
                {
                    "message_count": message_total,
                    "start_ts": start_ts,
                    "end_ts": end_ts,
                }
            )
            store = derived["visuals"]
            store.write_json(rid, "overview.json", overview_spec)
            store.write_json(rid, "zone_mix.json", vega_zone_mix({"zones": zone_mix}))
            store.write_json(rid, "transitions.json", vega_transitions({"transitions": transitions}))
            store.write_json(rid, "depth_dist.json", vega_depth_dist({"depths": depth_dist}))
            store.finalize_manifest(rid, inputs={"files": input_names})
            durations["visuals"] = perf_counter() - t0
            task_ok(log, "visuals", durations["visuals"], "specs=4")
        except Exception as exc:
            task_fail(log, "visuals", str(exc))
            raise typer.Exit(7)

    # Aggregator/report artifacts (derived aggregate domain + legacy surface)
    try:
        t0 = perf_counter()
        task_start(log, "aggregate")
        from ..aggregator.emit.run_report import build_run_report_from_derived, write_report_and_charts_from_derived

        ensure_domain("aggregate")
        aggregate_store = derived["aggregate"]
        report, chart_hashes, charts = build_run_report_from_derived("outputs/derived", rid)
        aggregate_store.write_json(rid, "run_report.json", report)
        for rel, payload in charts.items():
            aggregate_store.write_json(rid, rel, payload)
        aggregate_store.finalize_manifest(rid, inputs={"derived_root": "outputs/derived"})

        # Maintain compatibility for API consumers expecting outputs/report
        write_report_and_charts_from_derived("outputs/derived", rid, Path("outputs/report"))

        durations["aggregate"] = perf_counter() - t0
        task_ok(log, "aggregate", durations["aggregate"], f"charts={len(charts)} hashes={len(chart_hashes)}")
    except Exception as exc:
        # Non-fatal: downstream may surface missing run_report
        task_fail(log, "aggregate", str(exc))

    # Write final summary (always deterministic, even on failures later)
    try:
        summary = {
            "run_id": rid,
            "inputs": input_names,
            "durations": durations,
            "sessions": session_count,
            "messages": message_total,
        }
        out = Path("outputs/validation")
        out.mkdir(parents=True, exist_ok=True)
        (out / "pipeline_summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass

    log.info(f"[pipeline] done — run_id={rid}")


@app.callback()
def pipeline(
    input: str = typer.Option(..., "--input", help="Raw JSON file or directory"),
    db: Optional[str] = typer.Option(None, "--db", help="Path to create SQLite mirror (optional)"),
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Run ID for derived folders"),
    no_visuals: bool = typer.Option(False, "--no-visuals", help="Skip building visual specs"),
    semantic_memory: bool = typer.Option(True, "--semantic-memory/--no-semantic-memory", help="Compute semantic memory index and links"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing derived folders for this run_id"),
    privacy: str = typer.Option("pseudonymize", "--privacy", help="pseudonymize|redact|none"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase log detail (-v, -vv)"),
) -> None:
    run_pipeline_orchestrated(
        input=input,
        db=db,
        run_id=run_id,
        no_visuals=no_visuals,
        semantic_memory=semantic_memory,
        force=force,
        privacy=privacy,
        verbosity=verbose,
    )


if __name__ == "__main__":
    app()
