# Neurotrace API (MVP1)

Read-only FastAPI app exposing post-ingestion endpoints.

## Endpoints

- GET /health → {status: "ok"}
- GET /sessions → list[str] (max 100)
- GET /sessions/{id} → {session_id, message_count, start_ts, end_ts}
- GET /sessions/{id}/tree → {session_id, roots: [{id, children: [...]}, ...]}
- GET /sessions/{id}/visuals/{name} → Vega-Lite spec JSON
  - Supported names: overview, zone_mix
- GET /export/architect?out=exports/architect_v1 → {out, manifest} and writes files

## Determinism

- Stable ordering in queries and summaries.
- Visual specs use fixed width/height/fonts and sorted encodings.
- Golden tests verify sha256 hashes of summary/tree/zone_mix spec.

## CORS

- Disabled by default. Enable via server proxy or local tooling if needed.
