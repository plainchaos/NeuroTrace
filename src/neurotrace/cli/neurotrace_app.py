from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from neurotrace.ingest.load_raw import load_export
from neurotrace.ingest.validate import validate_raw_export
from neurotrace.ingest.normalize import normalize_messages
from neurotrace.ingest.privacy import pseudonymize, redact
from neurotrace.ingest.tagger import apply_tags
from neurotrace.ingest.metrics_pass import compute_session_metrics
from neurotrace.ingest.writer_sqlite import write_sqlite
from neurotrace.query.storage import open_db, fetch_distinct_conversations
from neurotrace import __version__
from neurotrace.config import DERIVED_ROOT
from .recompute import app as recompute_cli

app = typer.Typer(name="neurotrace")
tools = typer.Typer(name="tools")
migrate_app = typer.Typer(name="migrate")

app.add_typer(tools, name="tools")
app.add_typer(migrate_app, name="migrate")
app.add_typer(recompute_cli, name="recompute")

_DEF_SEED = Path(__file__).resolve().parents[3] / "tests/fixtures/seed/canonical_export_snippet.json"


def _resolve_input(path: Optional[str]) -> str:
    if path:
        return path
    if _DEF_SEED.exists():
        return str(_DEF_SEED)
    typer.echo(
        "ERROR: --input not provided and canonical seed not found at tests/fixtures/seed/canonical_export_snippet.json"
    )
    raise SystemExit(3)


@app.command()
def ingest(
    input: Optional[str] = typer.Option(None, help="Path to export .json or .zip"),
    db: str = typer.Option("conversations.db", help="SQLite DB path"),
    privacy: str = typer.Option("pseudonymize", help="pseudonymize|redact|none"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging"),
) -> None:
    try:
        input_path = _resolve_input(input)
        raw = load_export(input_path)
        records = list(normalize_messages(raw))
        if privacy == "redact":
            records = list(redact(records))  # type: ignore[assignment]
        else:
            records = list(pseudonymize(records))  # type: ignore[assignment]
        records = list(apply_tags(records))
        metrics = compute_session_metrics(records)
        write_sqlite(records, metrics, db)
        raise SystemExit(0)
    except FileNotFoundError as e:
        typer.echo(str(e))
        raise SystemExit(3)
    except Exception as e:
        typer.echo(f"ERROR: {e}")
        raise SystemExit(1)


@app.command()
def health(
    db: str = typer.Option("outputs/local_ci/smoke.db", help="SQLite DB path to check"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging"),
) -> None:
    """Run a quick health check: DB connectivity and one query."""
    try:
        with open_db(db) as conn:
            sessions = list(fetch_distinct_conversations(conn, limit=1))
        status = {
            "status": "ok",
            "db_path": db,
            "sessions_present": len(sessions) >= 1,
        }
        typer.echo(str(status))
        raise SystemExit(0)
    except FileNotFoundError:
        typer.echo(f"ERROR: DB not found: {db}")
        raise SystemExit(3)
    except Exception as e:
        typer.echo(f"ERROR: {e}")
        raise SystemExit(1)


@app.command()
def version() -> None:
    """Print package version."""
    typer.echo(__version__)


@app.command()
def validate(
    input: Optional[str] = typer.Option(None, help="Path to export .json or .zip"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging"),
) -> None:
    try:
        input_path = _resolve_input(input)
        raw = load_export(input_path)
        report = validate_raw_export(raw)
        typer.echo(str(report))
        raise SystemExit(0)
    except FileNotFoundError as e:
        typer.echo(str(e))
        raise SystemExit(3)
    except Exception as e:
        typer.echo(f"ERROR: {e}")
        raise SystemExit(1)


@app.command()
def metrics(
    input: Optional[str] = typer.Option(None, help="Path to export .json or .zip"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging"),
) -> None:
    try:
        input_path = _resolve_input(input)
        raw = load_export(input_path)
        records = list(normalize_messages(raw))
        records = list(pseudonymize(records))
        records = list(apply_tags(records))
        payload = compute_session_metrics(records)
        typer.echo(str(payload))
        raise SystemExit(0)
    except FileNotFoundError as e:
        typer.echo(str(e))
        raise SystemExit(3)
    except Exception as e:
        typer.echo(f"ERROR: {e}")
        raise SystemExit(1)


@app.command()
def pipeline(
    input: Optional[str] = typer.Option(None, help="Path to export .json or .zip"),
    db: str = typer.Option("conversations.db", help="SQLite DB path"),
    privacy: str = typer.Option("pseudonymize", help="pseudonymize|redact|none"),
    report: bool = typer.Option(True, "--report/--no-report", help="Build run_report and charts (legacy path)"),
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Run ID for derived folders"),
    no_visuals: bool = typer.Option(False, "--no-visuals", help="Skip building visual specs"),
    semantic_memory: bool = typer.Option(True, "--semantic-memory/--no-semantic-memory", help="Compute semantic memory index and links"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing derived folders"),
    verbose: int = typer.Option(0, "-v", "--verbose", count=True, help="Increase log detail (-v, -vv)"),
) -> None:
    """Run complete pipeline per blueprint (delegates to orchestrator)."""
    try:
        from .pipeline import run_pipeline_orchestrated

        run_pipeline_orchestrated(
            input=_resolve_input(input),
            db=None if not db else db,
            run_id=run_id,
            no_visuals=no_visuals or not report,
            semantic_memory=semantic_memory,
            force=force,
            privacy=privacy,
            verbosity=verbose,
        )
        raise SystemExit(0)
    except FileNotFoundError as e:
        typer.echo(str(e)); raise SystemExit(3)
    except Exception as e:
        typer.echo(f"ERROR: {e}"); raise SystemExit(1)


@migrate_app.command("metrics-json")
@tools.command("migrate-metrics")
def migrate_metrics(
    run_id: str = typer.Option(..., "--run-id", help="Run ID for derived folder"),
    metrics_root: str = typer.Option("outputs/metrics", help="Legacy metrics CSV root"),
) -> None:
    """Backfill: outputs/metrics CSV → outputs/derived/metrics/<run_id>/metrics.json + manifest.json.

    Computes sessions = count(summary/*.csv) and messages = sum of n_messages across summaries.
    """
    try:
        from pathlib import Path
        import csv
        from neurotrace.storage.derived import DerivedStore

        root = Path(metrics_root)
        sdir = root / "summary"
        if not sdir.exists():
            typer.echo("nothing to migrate: legacy summary directory not found; no changes made")
            raise SystemExit(0)

        summary_files = sorted(sdir.glob("*.csv"))
        if not summary_files:
            typer.echo("nothing to migrate: no legacy metrics CSV files found; no changes made")
            raise SystemExit(0)
        sessions = 0
        messages_total = 0
        per_session: dict[str, dict] = {}
        for p in summary_files:
            try:
                with p.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    n_msgs = 0
                    cid = p.stem
                    for row in reader:
                        if (row.get("metric") or "").strip() == "n_messages":
                            try:
                                n_msgs = int(float(row.get("value") or 0))
                            except Exception:
                                n_msgs = 0
                            break
                    messages_total += n_msgs
                    sessions += 1
                    per_session[cid] = {
                        "volume": n_msgs,
                        "depth": 0,
                        "zone_mix": {},
                        "transition_matrix": {},
                        "branching_factor": None,
                        "clarity_debt": None,
                        "jumpiness": None,
                        "stability": None,
                    }
            except Exception:
                # skip bad file
                continue

        payload = {
            "summary": {
                "sessions": sessions,
                "messages": messages_total,
            },
            "sessions": per_session,
        }
        store = DerivedStore("metrics")
        store.write_json(run_id, "metrics.json", payload)
        store.finalize_manifest(run_id, inputs={"legacy_root": str(root)})
        typer.echo(str(payload))
        raise SystemExit(0)
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(f"ERROR: {e}")
        raise SystemExit(1)


@app.command()
def report(
    run_id: str = typer.Option(None, help="Run ID to summarize"),
    latest: bool = typer.Option(False, "--latest", help="Pick newest run_id per domain if run_id not given"),
    list_runs: bool = typer.Option(False, "--list-runs", help="List discovered run_ids per domain and exit"),
) -> None:
    """Print a concise summary of manifests and artifacts across domains for a run_id."""
    root = DERIVED_ROOT
    domains = ["tagging", "transitions", "depth", "metrics", "analysis", "visuals", "aggregate"]
    summary = {"run_id": run_id, "domains": {}}
    import json as _json

    if list_runs:
        runs = {}
        for d in domains:
            droot = root / d
            if droot.exists():
                ids = sorted([p.name for p in droot.iterdir() if p.is_dir()])
                runs[d] = ids
        typer.echo(_json.dumps({"runs": runs}, ensure_ascii=False, sort_keys=True))
        raise SystemExit(0)

    # Resolve run_id if --latest
    if latest and not run_id:
        for pref in ("visuals",) + tuple(d for d in domains if d != "visuals"):
            droot = root / pref
            if droot.exists():
                ids = sorted([p.name for p in droot.iterdir() if p.is_dir()], reverse=True)
                if ids:
                    run_id = ids[0]
                    break
    if not run_id:
        typer.echo("ERROR: --run-id is required unless --latest is provided and a run exists")
        raise SystemExit(2)

    found_any = False
    for d in domains:
        p = root / d / run_id / "manifest.json"
        if p.exists():
            try:
                m = _json.loads(p.read_text(encoding="utf-8"))
                summary["domains"][d] = {
                    "artifact_count": len(m.get("artifacts", [])),
                    "artifacts": [a.get("name") for a in m.get("artifacts", [])],
                }
                found_any = True
            except Exception:
                summary["domains"][d] = {"error": "invalid manifest"}

    if not found_any:
        typer.echo(f"ERROR: No manifests found for run_id '{run_id}' under {root}")
        raise SystemExit(3)
    typer.echo(_json.dumps(summary, ensure_ascii=False, sort_keys=True))
