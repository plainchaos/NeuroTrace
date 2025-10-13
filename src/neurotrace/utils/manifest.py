from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any
import json


@dataclass
class ArtifactEntry:
    name: str
    sha256: str
    bytes: int


@dataclass
class Manifest:
    run_id: str
    domain: str
    inputs: Dict[str, Any]
    artifacts: List[ArtifactEntry]
    created_utc: str
    version: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

    def write(self, path: Path) -> None:
        path.write_text(self.to_json(), encoding="utf-8")


def iso_now_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


