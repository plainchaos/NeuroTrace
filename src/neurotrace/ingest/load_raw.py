from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict
from zipfile import ZipFile, BadZipFile


def _coerce_to_dict(payload: Any) -> Dict[str, Any]:
    # Blueprint requires Dict[str, Any]. If payload is a list of conversations,
    # wrap it under a stable key while preserving content.
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        return {"conversations": payload}
    # Fallback: represent as text to avoid type drift
    return {"data": payload}


def load_export(path: str) -> Dict[str, Any]:
    """Load ChatGPT export (json or json.zip) into a raw Python structure.

    Requirements:
    - Accepts plain JSON files or ZIP archives containing a JSON export
    - Preserves mapping trees and empty nodes; does not coerce types
    - Keeps attachments metadata and timestamps (even if null)
    - Deterministic behavior when multiple JSON files exist in a ZIP:
      the lexicographically smallest top-level JSON file is chosen.

    Raises:
    - FileNotFoundError if the input path does not exist
    - ValueError for unsupported extensions or unreadable ZIP contents
    - json.JSONDecodeError if the JSON is malformed
    """
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    if input_path.suffix.lower() == ".json":
        with input_path.open("r", encoding="utf-8") as f:
            return _coerce_to_dict(json.load(f))

    if input_path.suffix.lower() in {".zip", ".json.zip"}:
        try:
            with ZipFile(str(input_path), mode="r") as zf:
                # Candidate JSONs at any level; prefer top-level
                all_json = sorted([n for n in zf.namelist() if n.lower().endswith(".json")])
                if not all_json:
                    raise ValueError(f"No JSON file found in archive: {input_path}")
                # Prefer top-level JSONs first
                top_level = [n for n in all_json if "/" not in n.strip("/")]
                candidates = top_level if top_level else all_json
                chosen = candidates[0]
                with zf.open(chosen, mode="r") as f:
                    data_bytes = f.read()
                # Decode as UTF-8 with strict errors to avoid hidden drift
                text = data_bytes.decode("utf-8")
                return _coerce_to_dict(json.loads(text))
        except BadZipFile as e:
            raise ValueError(f"Invalid ZIP archive: {input_path}") from e

    raise ValueError(
        f"Unsupported input type: {input_path.name} (expected .json or .zip)"
    )
