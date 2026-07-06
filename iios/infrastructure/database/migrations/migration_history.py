"""
iios/infrastructure/database/migrations/migration_history.py
============================================================
Tracks which migrations have been applied, stored in _iios_migrations table.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Optional

from ..database_session import DatabaseSession
from ..database_constants import MigrationStatus, DEFAULT_MIGRATION_TABLE

__all__ = ["MigrationRecord", "MigrationHistory"]

_TABLE = DEFAULT_MIGRATION_TABLE
_DDL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    version     TEXT    NOT NULL UNIQUE,
    description TEXT    NOT NULL DEFAULT '',
    status      TEXT    NOT NULL DEFAULT 'PENDING',
    checksum    TEXT    NOT NULL DEFAULT '',
    applied_at  REAL,
    rolled_back_at REAL,
    duration_ms REAL    DEFAULT 0,
    error       TEXT
)
"""


@dataclass
class MigrationRecord:
    """Row representation of a migration history entry."""
    version: str
    description: str = ""
    status: str = MigrationStatus.PENDING.value
    checksum: str = ""
    applied_at: Optional[float] = None
    rolled_back_at: Optional[float] = None
    duration_ms: float = 0.0
    error: Optional[str] = None
    id: Optional[int] = None


class MigrationHistory:
    """CRUD layer for the migration history table."""

    def __init__(self, session: DatabaseSession) -> None:
        self._sess = session

    def ensure_table(self) -> None:
        self._sess.execute(_DDL)

    def insert(self, record: MigrationRecord) -> MigrationRecord:
        sql = (
            f"INSERT INTO {_TABLE} (version, description, status, checksum, applied_at, duration_ms) "
            "VALUES (?, ?, ?, ?, ?, ?)"
        )
        result = self._sess.execute(
            sql,
            (
                record.version,
                record.description,
                record.status,
                record.checksum,
                record.applied_at,
                record.duration_ms,
            ),
        )
        record.id = result.lastrowid
        return record

    def update_status(
        self,
        version: str,
        status: MigrationStatus,
        error: Optional[str] = None,
        duration_ms: float = 0.0,
    ) -> None:
        now = time.time()
        rolled_back_at = now if status == MigrationStatus.ROLLED_BACK else None
        applied_at = now if status == MigrationStatus.COMPLETED else None
        self._sess.execute(
            f"UPDATE {_TABLE} SET status=?, error=?, duration_ms=?, "
            "applied_at=COALESCE(applied_at, ?), rolled_back_at=? WHERE version=?",
            (status.value, error, duration_ms, applied_at, rolled_back_at, version),
        )

    def get(self, version: str) -> Optional[MigrationRecord]:
        row = self._sess.query_one(
            f"SELECT * FROM {_TABLE} WHERE version=?", (version,)
        )
        return _row_to_record(row) if row else None

    def get_all(self) -> list[MigrationRecord]:
        rows = self._sess.query(
            f"SELECT * FROM {_TABLE} ORDER BY version"
        )
        return [_row_to_record(r) for r in rows]

    def get_applied(self) -> list[MigrationRecord]:
        rows = self._sess.query(
            f"SELECT * FROM {_TABLE} WHERE status=? ORDER BY version",
            (MigrationStatus.COMPLETED.value,),
        )
        return [_row_to_record(r) for r in rows]

    def is_applied(self, version: str) -> bool:
        row = self._sess.query_one(
            f"SELECT status FROM {_TABLE} WHERE version=?", (version,)
        )
        return row is not None and row["status"] == MigrationStatus.COMPLETED.value

    def delete(self, version: str) -> bool:
        result = self._sess.execute(
            f"DELETE FROM {_TABLE} WHERE version=?", (version,)
        )
        return result.rowcount > 0


def _row_to_record(row: dict) -> MigrationRecord:
    return MigrationRecord(
        id=row.get("id"),
        version=row["version"],
        description=row.get("description", ""),
        status=row.get("status", MigrationStatus.PENDING.value),
        checksum=row.get("checksum", ""),
        applied_at=row.get("applied_at"),
        rolled_back_at=row.get("rolled_back_at"),
        duration_ms=row.get("duration_ms", 0.0),
        error=row.get("error"),
    )
