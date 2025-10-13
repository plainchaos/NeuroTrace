# Golden Outputs README

## Status: Active (MVP1 Post‑Ingestion)

This directory contains golden payloads and tests for the post‑ingestion API.

## Required Steps

### 1. What is covered
- Golden json payloads for:
  - `summary.json` (session rollup)
  - `tree.json` (acyclic roots list)
  - `zone_mix.json` (Vega‑Lite spec)
- Tests compare sha256 hashes computed with `neurotrace.eval.quality_gates.hash_json`.

### 2. Reproducing locally
```bash
pytest -q tests/goldens/post_ingestion/test_post_ingestion_goldens.py
```

### 3. Updating goldens
If the seed or deterministic ordering changes legitimately:
1. Rebuild from the seed in a temp DB in tests (the test does this).
2. Capture the new payloads and replace `summary.json`, `tree.json`, `zone_mix.json`.
3. Commit with rationale in `CHANGELOG.md` and link to acceptance.

### 3. Update Manifest
Update `manifest.json` with:
- Actual file sizes
- Real SHA256 checksums
- Correct file paths
- Generation timestamp

## TODOs

### Cannot Generate Currently
- **Reason**: Current codebase has incomplete dependencies
- **Fix**: Update requirements.txt with missing packages (pandas, matplotlib, numpy, seaborn)
- **Impact**: Pipeline cannot run until dependencies are fixed

### Schema Issues
- **Reason**: cognitive_tags table has PK discrepancy between README and code
- **Fix**: Choose between composite PK (README) vs single PK (code)
- **Impact**: Database creation may fail

### Missing Metrics
- **Reason**: 4 out of 8 MVP metrics are not implemented
- **Fix**: Implement stub functions for branching_factor, clarity_debt, jumpiness, stability
- **Impact**: Metrics computation will be incomplete

### CLI
The project now exposes `neurotrace` CLI with `serve`, `export-architect`, `privacy-audit`.

## Expected Outputs

### Metrics (CSV files)
- `metrics/breadcrumbs/conversation_001.csv` - Message breadcrumbs with cognitive zones
- `metrics/transitions/conversation_001.csv` - Zone transition counts
- `metrics/summary/conversation_001.csv` - Summary statistics
- `metrics/tags/conversation_001.csv` - Cognitive function tags

### Visuals (PNG files)
- `visuals/figure4_zone_transition.png` - Zone transition heatmap
- `visuals/figure6_modular_flow.png` - Modular flow diagram

### Validation
- All files must exist and be readable
- CSV files must have correct column headers
- PNG files must be valid image format
- Checksums must match expected values

## Next Steps

1. **Fix Dependencies**: Update requirements.txt
2. **Resolve Schema**: Choose PK strategy for cognitive_tags
3. **Implement Missing Metrics**: Add stub functions
4. **Update CLI**: Implement new command structure
5. **Run Pipeline**: Generate actual golden outputs
6. **Validate**: Ensure all outputs match expectations

# Goldens

These are initial placeholder goldens for MVP1 ingestion smoke test.

- Seed: `tests/fixtures/seed/canonical_export_snippet.json`
- Generated at: 2025-09-24

## Hashes

Pending first CI run; will record and lock after green.
