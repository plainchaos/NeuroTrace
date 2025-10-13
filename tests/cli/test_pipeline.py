from __future__ import annotations

import json
from pathlib import Path
import pytest


def _write_session(tmp: Path, name: str = "s1.json", messages: int = 3) -> Path:
    msgs = []
    for i in range(messages):
        msgs.append({
            "id": f"m{i}",
            "role": "assistant" if i % 2 == 0 else "user",
            "content": f"hello {i}",
            "create_time": i,
        })
    sess = {"id": "s1", "messages": msgs}
    p = tmp / name
    p.write_text(json.dumps(sess, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return p


def test_pipeline_happy_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Work in a temp cwd so outputs/* are isolated
    monkeypatch.chdir(tmp_path)

    # Create a minimal session json
    sess = _write_session(tmp_path)

    # Import and run orchestrator
    from neurotrace.cli.pipeline import run_pipeline_orchestrated

    run_pipeline_orchestrated(
        input=str(sess),
        db=None,
        run_id="TESTRUN",
        no_visuals=False,
        semantic_memory=False,
        force=True,
        privacy="none",
        verbosity=0,
    )

    # Assert derived artifacts exist
    droot = tmp_path / "outputs" / "derived"
    assert (droot / "transitions" / "TESTRUN" / "transitions.json").exists()
    assert (droot / "depth" / "TESTRUN" / "depth_dist.json").exists()
    assert (droot / "metrics" / "TESTRUN" / "metrics.json").exists()
    assert (droot / "visuals" / "TESTRUN" / "overview.json").exists()
    assert (droot / "aggregate" / "TESTRUN" / "run_report.json").exists()
    assert (droot / "aggregate" / "TESTRUN" / "charts" / "zone_totals.json").exists()

    # Report artifacts
    rroot = tmp_path / "outputs" / "report"
    assert (rroot / "run_report.json").exists()
    assert (rroot / "run_manifest.json").exists()

    # Golden check for metrics
    m = json.loads((droot / "metrics" / "TESTRUN" / "metrics.json").read_text(encoding="utf-8"))
    golden = json.loads((Path(__file__).resolve().parents[1] / "goldens" / "pipeline" / "metrics.json").read_text(encoding="utf-8"))
    assert m == golden


def test_pipeline_fail_fast_missing_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    from neurotrace.cli.pipeline import run_pipeline_orchestrated
    import typer

    with pytest.raises(typer.Exit) as ex:
        run_pipeline_orchestrated(
            input=str(tmp_path / "missing.json"),
            db=None,
            run_id="FAILRUN",
            no_visuals=True,
            semantic_memory=False,
            force=False,
            privacy="pseudonymize",
            verbosity=0,
        )
    assert ex.value.exit_code == 3


def test_pipeline_fail_fast_empty_sessions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    empty = tmp_path / "unsupported.json"
    empty.write_text("{}", encoding="utf-8")

    from neurotrace.cli.pipeline import run_pipeline_orchestrated
    import typer

    with pytest.raises(typer.Exit) as ex:
        run_pipeline_orchestrated(
            input=str(empty),
            db=None,
            run_id="EMPTYRUN",
            no_visuals=True,
            semantic_memory=False,
            force=False,
            privacy="pseudonymize",
            verbosity=0,
        )
    assert ex.value.exit_code == 4

    derived_root = tmp_path / "outputs" / "derived"
    assert not derived_root.exists()
