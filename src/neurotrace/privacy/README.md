# Privacy Audit (MVP1)

Rule-based scan of `message_contents` for PII markers.

## Command

```
neurotrace privacy-audit --db conversations.db --sample-limit 1000
```

## Output

- Writes `outputs/privacy/audit.json` with:
  - `status`: "OK" or "FAIL"
  - `records_scanned`: number of rows scanned
  - `hits`: counts per marker (email, phone, url)

## Determinism

- Deterministic query ordering; scanning is limited by `sample_limit`.
- No random sampling in MVP1.
