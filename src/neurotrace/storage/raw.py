from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional

from ..utils.fs import get_project_root


class RawSource:
    """Read-only access to canonical raw data.

    Supports JSON root under project `data/raw_json/` and optional SQLite mirror (read-only).
    """

    def __init__(self, json_root: Optional[Path] = None, sqlite_path: Optional[Path] = None) -> None:
        root = get_project_root()
        self.json_root = json_root or (root / "data")
        self.sqlite_path = sqlite_path or (root / "data" / "sqlite" / "neurotrace.db")

    def iter_session_ids(self) -> Iterator[str]:
        if self.json_root.exists():
            for p in sorted(self.json_root.glob("*.json")):
                yield p.stem

    def read_session(self, session_id: str) -> Dict:
        path = self.json_root / f"{session_id}.json"
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)


