"""
iios/infrastructure/database/migrations/schema_version.py
==========================================================
Schema version tracking — records the overall DB schema semver.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..database_session import DatabaseSession
from ..database_constants import DEFAULT_SCHEMA_VERSION_TABLE

__all__ = ["SchemaVersion", "SchemaVersionTracker"]

_TABLE = DEFAULT_SCHEMA_VERSION_TABLE
_DDL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    version    TEXT    NOT NULL,
    updated_at REAL    NOT NULL
)
"""


@dataclass
class SchemaVersion:
    version: str
    updated_at: float
    id: Optional[int] = None


class SchemaVersionTracker:
    """Tracks a single current schema version in the DB."""

    def __init__(self, session: DatabaseSession) -> None:
        self._sess = session

    def ensure_table(self) -> None:
        self._sess.execute(_DDL)

    def get_current(self) -> Optional[str]:
        row = self._sess.query_one(
            f"SELECT version FROM {_TABLE} ORDER BY id DESC LIMIT 1"
        )
        return row["version"] if row else None

    def set_version(self, version: str) -> None:
        import time
        self._sess.execute(
            f"INSERT INTO {_TABLE} (version, updated_at) VALUES (?, ?)",
            (version, time.time()),
        )

    def history(self) -> list[SchemaVersion]:
        rows = self._sess.query(
            f"SELECT * FROM {_TABLE} ORDER BY id DESC"
        )
        return [
            SchemaVersion(id=r["id"], version=r["version"], updated_at=r["updated_at"])
            for r in rows
        ]
