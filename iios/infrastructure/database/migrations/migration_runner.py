"""
iios/infrastructure/database/migrations/migration_runner.py
============================================================
Runs individual migrations (up / down) against a DatabaseSession.
"""

from __future__ import annotations

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from ..database_session import DatabaseSession
from ..database_constants import MigrationStatus
from ..database_exceptions import MigrationError
from .migration_history import MigrationHistory, MigrationRecord

__all__ = ["Migration", "MigrationRunner"]

_LOG = logging.getLogger("iios.database.migrations")


class Migration(ABC):
    """Abstract base for all IIOS database migrations.

    Each migration must declare a unique ``version`` string (e.g. "0001")
    and human-readable ``description``.

    Usage::

        class AddTradesTable(Migration):
            version = "0001"
            description = "Create trades table"

            def up(self) -> list[str]:
                return [
                    '''CREATE TABLE IF NOT EXISTS trades (
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           symbol TEXT NOT NULL,
                           qty    INTEGER NOT NULL DEFAULT 0
                       )'''
                ]

            def down(self) -> list[str]:
                return ["DROP TABLE IF EXISTS trades"]
    """

    version: str = ""
    description: str = ""

    @abstractmethod
    def up(self) -> list[str]:
        """Return list of SQL statements to apply this migration."""

    @abstractmethod
    def down(self) -> list[str]:
        """Return list of SQL statements to roll back this migration."""

    def checksum(self) -> str:
        """Stable checksum of the up() statements for integrity validation."""
        content = "\n".join(self.up())
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class MigrationRunner:
    """Applies and rolls back Migration objects against a session."""

    def __init__(
        self,
        session: DatabaseSession,
        validate_checksum: bool = True,
    ) -> None:
        self._sess = session
        self._validate = validate_checksum
        self._history = MigrationHistory(session)

    def apply(self, migration: Migration) -> MigrationRecord:
        """Apply migration.up() if not already applied."""
        self._history.ensure_table()

        if self._history.is_applied(migration.version):
            existing = self._history.get(migration.version)
            if self._validate and existing and existing.checksum != migration.checksum():
                from ..database_exceptions import MigrationConflictError
                raise MigrationConflictError(
                    migration.version,
                    existing.checksum,
                    migration.checksum(),
                )
            _LOG.debug("Migration %s already applied — skipping", migration.version)
            return existing  # type: ignore[return-value]

        record = MigrationRecord(
            version=migration.version,
            description=migration.description,
            status=MigrationStatus.RUNNING.value,
            checksum=migration.checksum(),
        )
        self._history.insert(record)

        t0 = time.monotonic()
        try:
            for sql in migration.up():
                self._sess.execute(sql)
            duration_ms = (time.monotonic() - t0) * 1000
            self._history.update_status(
                migration.version,
                MigrationStatus.COMPLETED,
                duration_ms=duration_ms,
            )
            record.status = MigrationStatus.COMPLETED.value
            record.duration_ms = duration_ms
            _LOG.info("Applied migration %s (%s) in %.1fms", migration.version, migration.description, duration_ms)
            return record
        except Exception as exc:
            duration_ms = (time.monotonic() - t0) * 1000
            self._history.update_status(
                migration.version,
                MigrationStatus.FAILED,
                error=str(exc),
                duration_ms=duration_ms,
            )
            raise MigrationError(
                f"Migration {migration.version} failed: {exc}",
                code="DB-MIG-003",
                context={"version": migration.version},
            ) from exc

    def rollback(self, migration: Migration) -> bool:
        """Roll back a migration using migration.down()."""
        self._history.ensure_table()
        if not self._history.is_applied(migration.version):
            _LOG.warning("Migration %s is not applied — cannot roll back", migration.version)
            return False

        try:
            for sql in migration.down():
                self._sess.execute(sql)
            self._history.update_status(migration.version, MigrationStatus.ROLLED_BACK)
            _LOG.info("Rolled back migration %s", migration.version)
            return True
        except Exception as exc:
            raise MigrationError(
                f"Rollback of {migration.version} failed: {exc}",
                code="DB-MIG-004",
                context={"version": migration.version},
            ) from exc
