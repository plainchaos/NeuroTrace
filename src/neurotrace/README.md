# Neurotrace Framework (MVP1)

## Overview

Neurotrace is a Python framework for deterministic, file-first analytics over conversational data. It ingests raw exports, computes stable derived artifacts, and exposes a read‑only API and CLI to serve and summarize precomputed results. All compute happens via the CLI; the API is strictly read‑only.

Key principles:
- Single write path: CLI `recompute` commands write artifacts.
- Read‑only API: serves precomputed specs and summaries; no writes.
- Determinism: same inputs ⇒ same outputs. Stable ordering, fixed seeds, no UUIDs in data, timestamps only in manifests.
- File-first: artifacts live under `outputs/derived/<domain>/<run_id>/` with a `manifest.json` of content hashes and sizes.

## Architecture

Package layout:
```
src/neurotrace/
  analytics/       # compute-only entry points (tagging, transitions, depth, metrics, semantic)
  storage/         # RawSource (read-only), DerivedStore (manifests)
  visuals/         # display-only spec builders (Vega-Lite JSON)
  cli/             # Typer app: recompute, report, health, version
  api/             # FastAPI (read-only)
  utils/           # fs/hash/manifest/log
  config.py        # frozen defaults (no env)
```

Derived domains and artifacts:
- `tagging` → `tags.json`
- `transitions` → `zone_mix.json`, `transitions.json`
- `depth` → `depth_dist.json`
- `metrics` → `metrics.json`
- `analysis` (semantic memory) → `semantic_index.json`, `semantic_links.json`
- `visuals` (display-only specs) → `overview.json`, `zone_mix.json`, `transitions.json`, `depth_dist.json`

Each domain and run writes `outputs/derived/<domain>/<run_id>/{artifacts..., manifest.json}`. Manifests include `{name, sha256, bytes}` per artifact.

## CLI

Entry points:
- `python -m neurotrace` (module entry)
- Importable: `from neurotrace.cli import app`

Commands:
```bash
# Compute derived artifacts (writes under outputs/derived/<domain>/<run_id>/)
python -m neurotrace recompute tagging --run-id 20251001T120000Z
python -m neurotrace recompute transitions --run-id 20251001T120000Z
python -m neurotrace recompute depth --run-id 20251001T120000Z
python -m neurotrace recompute metrics --run-id 20251001T120000Z
python -m neurotrace recompute semantic-memory --run-id 20251001T120000Z
python -m neurotrace recompute visuals --run-id 20251001T120000Z

# Report (read-only): summarize manifests across domains for a run
python -m neurotrace report --run-id 20251001T120000Z
python -m neurotrace report --latest        # pick newest run per domain
python -m neurotrace report --list-runs     # list discovered run_ids per domain

# Health & Version
python -m neurotrace health
python -m neurotrace version
```

Run‑ID policy: if `--run-id` is omitted, CLI generates `yyyyMMddTHHmmssZ` (UTC) for folder naming only; timestamps are never embedded in data.

## API (Read‑Only)

Endpoints (served by FastAPI app in `neurotrace.api.http`):
- `GET /health` → `{schema_hash, golden_hash|null, version}`
- `GET /sessions?limit=100&offset=0` → `[{id, started_at, message_count}]`
- `GET /sessions/{id}` → per‑session summary
- `GET /sessions/{id}/tree` → acyclic tree
- `GET /sessions/{id}/visuals/{name}` → Vega spec (`overview|zone_mix|depth_dist|transitions`)

Note: API performs no writes; visuals are display‑only JSON specs.

## Determinism & Manifests

- Hashing: SHA‑256 of file content; file sizes recorded in bytes.
- JSON encoding: UTF‑8, sorted keys; rounded numeric presentation where required.
- Timestamps: recorded only in `manifest.json` (`created_utc`).
- `/health` returns stable hashes (e.g., latest visuals manifest/specs hash).

## Config (No Env)

Frozen defaults live in `neurotrace/config.py`:
- `RAW_JSON_ROOT = <project>/data/raw_json`
- `RAW_SQLITE_PATH = <project>/data/sqlite/neurotrace.db` (optional, read‑only)
- `DERIVED_ROOT = <project>/outputs/derived`
- `RUN_ID_FORMAT = "%Y%m%dT%H%M%SZ"`
- Visual defaults: width=960, height=540, font="system‑ui, sans‑serif"
- Pipeline computes semantic memory by default; disable with `--no-semantic-memory`.
- Heavy embedding features remain OFF by default.

Overrides are accepted only via CLI flags (no environment variables). A policy test enforces zero usage of `os.environ`/`getenv` in package code.

## Outputs

```
outputs/derived/
  tagging/<run_id>/        tags.json, manifest.json
  transitions/<run_id>/    zone_mix.json, transitions.json, manifest.json
  depth/<run_id>/          depth_dist.json, manifest.json
  metrics/<run_id>/        metrics.json, manifest.json
  analysis/<run_id>/       semantic_index.json, semantic_links.json, manifest.json
  visuals/<run_id>/        overview.json, zone_mix.json, transitions.json, depth_dist.json, manifest.json
```

## Tests

- Unit, integration, and golden tests validate determinism and read‑only behavior.
- Policy: fail on any use of environment variables inside `src/neurotrace/**`.
- Smoke: `report --run-id <id>` works with constants only; no env required.

## Notes

- Status/Health docs and local CI scripts live under `Cursor_Agent_Management/`.
- Privacy audit outputs under `outputs/privacy/` (read‑only).
Recompute also accepts export-style inputs via `--input` with the same accepted
shapes as the pipeline (JSON list of sessions, a dict with
`conversations`/`items`/`threads`, a dict with `messages`, or a directory of
`*.json`).

Examples:
  python -m neurotrace recompute semantic-memory --input data/export.json --run-id 20251001T120000Z
  python -m neurotrace recompute tagging --input data/export.json --run-id 20251001T120000Z
