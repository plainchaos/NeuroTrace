from __future__ import annotations

import json
from pathlib import Path
import pytest


def _write_session(tmp: Path, name: str = "s1.json", messages: int = 3) -> Path:
    msgs = []
    for i in range(messages):
        msgs.append(
            {
                "id": f"m{i}",
                "role": "assistant" if i % 2 == 0 else "user",
                "content": f"hello {i}",
                "create_time": i,
            }
        )
    sess = {"id": "s1", "messages": msgs}
    p = tmp / name
    p.write_text(json.dumps(sess, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return p


def test_recompute_semantic_memory_with_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Run in isolated cwd so outputs/* are contained
    monkeypatch.chdir(tmp_path)

    # Minimal session json
    sess = _write_session(tmp_path)

    from neurotrace.cli.recompute import recompute_semantic_memory

    recompute_semantic_memory(run_id="RS1", enable_embeddings=False, input=str(sess), verbose=0)

    droot = tmp_path / "outputs" / "derived" / "analysis" / "RS1"
    assert (droot / "semantic_index.json").exists()
    assert (droot / "semantic_links.json").exists()
    assert (droot / "manifest.json").exists()


def test_recompute_semantic_memory_fail_fast_unsupported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    payload = tmp_path / "unsupported.json"
    payload.write_text("{}", encoding="utf-8")

    from neurotrace.cli.recompute import recompute_semantic_memory
    import typer

    with pytest.raises(typer.Exit) as ex:
        recompute_semantic_memory(run_id="RS_BAD", enable_embeddings=False, input=str(payload), verbose=0)
    assert ex.value.exit_code == 4
    assert not (tmp_path / "outputs" / "derived").exists()


def test_recompute_tagging_with_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    sess = _write_session(tmp_path)

    from neurotrace.cli.recompute import recompute_tagging

    recompute_tagging(run_id="RS2", input=str(sess), verbose=0)

    droot = tmp_path / "outputs" / "derived" / "tagging" / "RS2"
    assert (droot / "tags.json").exists()
    assert (droot / "manifest.json").exists()
