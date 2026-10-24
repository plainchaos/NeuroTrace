# Neurotrace

Deterministic, file-first analytics over conversational data. The CLI computes stable derived artifacts; the API is strictly read‑only and serves precomputed specs.

## Quickstart

```bash
pip install -e .
python -m neurotrace --help
```

To run the test suite, install the test extras first:

```bash
pip install -e ".[test]"
pytest -q
```

## One-shot pipeline (JSON-first derived artifacts)

Run the complete flow in one command (ingest → analytics → visuals → report). Artifacts are written under `outputs/derived/<domain>/<run_id>/` as JSON with a `manifest.json` per domain.

```bash
neurotrace pipeline --input data/export.json --db conversations.db

# Redact instead of pseudonymize
neurotrace pipeline --input data/export.json --privacy redact

# Generate report from derived JSON (default)
neurotrace pipeline --input data/export.json

# Semantic memory is ON by default; disable with:
neurotrace pipeline --input data/export.json --no-semantic-memory
```

Outputs:
- Derived JSON domains: `outputs/derived/{tagging,transitions,depth,metrics,analysis,visuals}/<run_id>/*`
- Report: `outputs/report/{run_report.json, run_manifest.json, charts/*}` (built from derived JSON)
- Optional DB mirror: `conversations.db` (read-only; not used by report)

## Derived pipelines (CLI)

Write artifacts under `outputs/derived/<domain>/<run_id>/` (with `manifest.json`):

```bash
# Compute domains
python -m neurotrace recompute tagging --input data/conversation.json --db data/neurotrace.db --run-id 20251001T120000Z
python -m neurotrace recompute transitions --input data/conversation.json  --db data/neurotrace.db --run-id 20251001T120000Z
python -m neurotrace recompute depth --input data/conversation.json  --db data/neurotrace.db --run-id 20251001T120000Z
python -m neurotrace recompute metrics --input data/conversation.json  --db data/neurotrace.db --run-id 20251001T120000Z
python -m neurotrace recompute semantic-memory --input data/conversation.json  --db data/neurotrace.db --run-id 20251001T120000Z
python -m neurotrace recompute visuals --input data/conversation.json  --db data/neurotrace.db --run-id 20251001T120000Z

# Summarize manifests (read-only)
python -m neurotrace report --run-id 20251001T120000Z
python -m neurotrace report --latest
python -m neurotrace report --list-runs

# Migrate legacy CSVs (read-only conversion)
python -m neurotrace migrate metrics-json --run-id 20251001T120000Z

# Health & version
python -m neurotrace health
python -m neurotrace version
```

## API (read‑only)

- `GET /health` → `{schema_hash, golden_hash|null, version}`
- `GET /sessions?limit=100&offset=0` → `[{id, started_at, message_count}]`
- `GET /sessions/{id}` → summary JSON
- `GET /sessions/{id}/tree` → acyclic tree
- `GET /sessions/{id}/visuals/{name}` → Vega spec (`overview|zone_mix|depth_dist|transitions`)

The API performs no writes; visuals are deterministic JSON specs only. Report endpoint prefers derived JSON; legacy CSV fallback is temporary and will be removed after migration.

## Outputs

```
outputs/derived/
  tagging/<run_id>/        tags.json, manifest.json
  transitions/<run_id>/    zone_mix.json, transitions.json, manifest.json
  depth/<run_id>/          depth_dist.json, manifest.json
  metrics/<run_id>/        metrics.json, manifest.json
  analysis/<run_id>/       semantic_index.json, semantic_links.json, manifest.json
  visuals/<run_id>/        overview.json, zone_mix.json, transitions.json, depth_dist.json, manifest.json
  aggregate/<run_id>/      run_report.json, charts/*.json, manifest.json
```

## Determinism

- Same inputs ⇒ same outputs. Stable ordering; no UUIDs in data.
- JSON encoding: UTF‑8 with sorted keys; timestamps only in `manifest.json`.
- Hashing: SHA‑256 over artifact content.

## Config (no env)

Frozen defaults in `src/neurotrace/config.py`:
- `RAW_JSON_ROOT = <project>/data/raw_json`
- `DERIVED_ROOT = <project>/outputs/derived`
- `RUN_ID_FORMAT = "%Y%m%dT%H%M%SZ"`
- Visual defaults: width=960, height=540, font="system‑ui, sans‑serif"
- Pipeline computes semantic memory by default; disable with `--no-semantic-memory`.
- Heavy embedding features remain OFF by default.

Overrides only via CLI flags; environment variables are not used.
