from __future__ import annotations

from pathlib import Path

# Frozen defaults — do not read from environment; override only via CLI flags.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_JSON_ROOT = PROJECT_ROOT / "data" / "conversation.json"
RAW_SQLITE_PATH = PROJECT_ROOT / "data" / "neurotrace.db"  # optional, read-only
DERIVED_ROOT = PROJECT_ROOT / "outputs" / "derived"

# Run-ID format used for folder names only (not embedded into data)
RUN_ID_FORMAT = "%Y%m%dT%H%M%SZ"  # yyyyMMddTHHmmssZ (UTC)

# Visual spec presentation defaults
VISUAL_WIDTH = 960
VISUAL_HEIGHT = 540
VISUAL_FONT_FAMILY = "system-ui, sans-serif"

# Semantic memory heavy ops are OFF by default
SEMANTIC_HEAVY_DEFAULT_OFF = True
