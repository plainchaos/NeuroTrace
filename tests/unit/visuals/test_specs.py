from __future__ import annotations

from neurotrace.visuals.api_specs import vega_session_overview, vega_zone_mix
from neurotrace.eval.quality_gates import hash_json


def test_overview_spec_hash_stable():
    summary = {"message_count": 5, "start_ts": 1.0, "end_ts": 3.0}
    spec = vega_session_overview(summary)
    h = hash_json(spec)
    assert isinstance(h, str) and len(h) == 64


def test_zone_mix_spec_hash_stable_sorted():
    summary = {"zones": [{"zone": "B", "count": 2}, {"zone": "A", "count": 3}]}
    spec = vega_zone_mix(summary)
    h = hash_json(spec)
    spec2 = vega_zone_mix({"zones": list(reversed(summary["zones"]))})
    h2 = hash_json(spec2)
    assert h == h2



