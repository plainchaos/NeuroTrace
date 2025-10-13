from __future__ import annotations

from pathlib import Path
import json
import pytest

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # pragma: no cover - handled in CI where dependency missing
    pytest.skip("jsonschema is required for observability schema tests", allow_module_level=True)


def test_log_schemas_are_valid_jsonschema():
    # Repo root: tests/.. (parents[2])
    repo = Path(__file__).resolve().parents[2]
    schemas_dir = repo / "tests" / "fixtures" / "logs" / "schemas"
    for p in [
        schemas_dir / "decisions.schema.json",
        schemas_dir / "errors.schema.json",
        schemas_dir / "ownership.schema.json",
        schemas_dir / "sessions.schema.json",
    ]:
        data = json.loads(p.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(data)

