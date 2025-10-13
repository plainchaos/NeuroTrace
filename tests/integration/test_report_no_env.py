from __future__ import annotations

from pathlib import Path
from typer.testing import CliRunner

from neurotrace.cli import app
from neurotrace.config import DERIVED_ROOT


def test_report_works_with_run_id_no_env(tmp_path):
    # Use VISRUN from earlier smokes if present; otherwise, skip
    visroot = DERIVED_ROOT / "visuals"
    runs = sorted([p.name for p in visroot.iterdir() if p.is_dir()]) if visroot.exists() else []
    if not runs:
        return
    run_id = runs[-1]
    r = CliRunner().invoke(app, ["report", "--run-id", run_id])
    assert r.exit_code == 0
    assert "\"domains\"" in r.stdout

