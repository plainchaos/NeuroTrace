"""Query/DAO and summary utilities (read-only).

These modules provide a thin, parameterized SQL layer over the Neurotrace
SQLite schema. All functions are read-only and designed to be stable against
the canonical schema in `schema/create.sql`.
"""

__all__ = [
    "open_db",
]

from .storage import open_db  # re-export for convenience


