from __future__ import annotations

from typing import Optional

import typer

from neurotrace.ingest.load_raw import load_export
from neurotrace.ingest.validate import validate_raw_export
from neurotrace.ingest.normalize import normalize_messages
from neurotrace.ingest.privacy import pseudonymize, redact
from neurotrace.ingest.tagger import apply_tags
from neurotrace.ingest.metrics_pass import compute_session_metrics
from neurotrace.ingest.writer_sqlite import write_sqlite


app = typer.Typer(name="neurotrace")


@app.command()
def ingest(
    input: str = typer.Option(..., help="Path to export .json or .zip"),
    db: str = typer.Option("conversations.db", help="SQLite DB path"),
    privacy: str = typer.Option("pseudonymize", help="pseudonymize|redact"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging"),
) -> None:
    try:
        raw = load_export(input)
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
def validate(
    input: str = typer.Option(..., help="Path to export .json or .zip"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging"),
) -> None:
    try:
        raw = load_export(input)
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
    input: str = typer.Option(..., help="Path to export .json or .zip"),
    verbose: bool = typer.Option(False, "--verbose", help="Enable debug logging"),
) -> None:
    try:
        raw = load_export(input)
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


