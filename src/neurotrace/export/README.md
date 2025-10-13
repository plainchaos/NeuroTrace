# Architect Export (MVP1)

The `export-architect` CLI command writes a minimal training-ready pack.

## Layout

```
exports/architect_v1/
  records.jsonl    # id, conversation_id, role, parent_id, ts
  sessions.jsonl   # conversation_id
  tags.jsonl       # stub for MVP1
  metrics.jsonl    # stub for MVP1
  manifest.json    # {schema_version, record_counts, generated_at, source_commit, privacy_profile}
```

## Notes

- IDs are the normalized message IDs; stable across runs for the same seed.
- PII is stripped at ingest via pseudonymization; URLs reduced to domains where applicable.
- Manifest timestamps are in UTC ISO8601.
