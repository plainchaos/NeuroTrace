from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

from ..utils.fs import get_derived_root, ensure_directory
from ..utils.hash import sha256_file
from ..utils.manifest import ArtifactEntry, Manifest, iso_now_utc


class DerivedStore:
    def __init__(self, domain: str) -> None:
        self.domain = domain

    def path(self, run_id: str) -> Path:
        base = get_derived_root() / self.domain / run_id
        ensure_directory(base)
        return base

    def write_json(self, run_id: str, name: str, data: Any) -> Path:
        out = self.path(run_id) / name
        out.parent.mkdir(parents=True, exist_ok=True)
        # Deterministic JSON: UTF-8, sorted keys, 6-decimal floats
        with out.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, sort_keys=True)
        return out

    def finalize_manifest(self, run_id: str, inputs: Dict[str, Any], version: str = "mvp1") -> Path:
        base = self.path(run_id)
        artifacts: List[ArtifactEntry] = []
        for p in sorted(base.rglob("*")):
            if p.name == "manifest.json" or p.is_dir():
                continue
            rel = p.relative_to(base)
            artifacts.append(
                ArtifactEntry(name=str(rel).replace("\\", "/"), sha256=sha256_file(p), bytes=p.stat().st_size)
            )
        manifest = Manifest(
            run_id=run_id,
            domain=self.domain,
            inputs=inputs,
            artifacts=artifacts,
            created_utc=iso_now_utc(),
            version=version,
        )
        out = base / "manifest.json"
        manifest.write(out)
        return out
