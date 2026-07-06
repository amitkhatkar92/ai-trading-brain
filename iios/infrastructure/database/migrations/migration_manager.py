"""
iios/infrastructure/database/migrations/migration_manager.py
============================================================
Orchestrates a list of migrations — apply, rollback, status.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..database_engine import DatabaseEngine
from ..database_session import DatabaseSession
from ..database_exceptions import MigrationNotFoundError, MigrationAlreadyAppliedError
from .migration_runner import Migration, MigrationRunner
from .migration_history import MigrationHistory, MigrationRecord
from .schema_version import SchemaVersionTracker

__all__ = ["MigrationManager"]

_LOG = logging.getLogger("iios.database.migrations")


class MigrationManager:
    """Registers migrations and applies them in version order.

    Usage::

        mgr = MigrationManager(engine)
        mgr.register(AddTradesTable())
        mgr.register(AddIndexOnSymbol())
        mgr.migrate()  # applies all pending migrations

        # Rollback to a specific version
        mgr.rollback_to("0001")
    """

    def __init__(
        self,
        engine: DatabaseEngine,
        validate_checksum: bool = True,
    ) -> None:
        self._engine = engine
        self._validate = validate_checksum
        self._migrations: dict[str, Migration] = {}

    def register(self, migration: Migration) -> None:
        if not migration.version:
            raise ValueError(f"Migration {type(migration).__name__} has no version")
        self._migrations[migration.version] = migration

    def register_many(self, *migrations: Migration) -> None:
        for m in migrations:
            self.register(m)

    def migrate(self) -> list[MigrationRecord]:
        """Apply all pending (not yet applied) migrations in version order."""
        applied = []
        ordered = sorted(self._migrations.values(), key=lambda m: m.version)

        with self._engine.session() as sess:
            runner = MigrationRunner(sess, validate_checksum=self._validate)
            history = MigrationHistory(sess)
            history.ensure_table()

            for migration in ordered:
                if not history.is_applied(migration.version):
                    record = runner.apply(migration)
                    applied.append(record)

            if applied:
                tracker = SchemaVersionTracker(sess)
                tracker.ensure_table()
                tracker.set_version(ordered[-1].version)

        return applied

    def rollback_to(self, target_version: str) -> list[MigrationRecord]:
        """Roll back all migrations applied after *target_version* (inclusive on those > target)."""
        rolled = []
        ordered = sorted(self._migrations.values(), key=lambda m: m.version, reverse=True)

        with self._engine.session() as sess:
            history = MigrationHistory(sess)
            runner = MigrationRunner(sess, validate_checksum=False)
            applied = {r.version for r in history.get_applied()}

            for migration in ordered:
                if migration.version <= target_version:
                    break
                if migration.version in applied:
                    ok = runner.rollback(migration)
                    if ok:
                        rec = history.get(migration.version)
                        if rec:
                            rolled.append(rec)

        return rolled

    def rollback_last(self) -> Optional[MigrationRecord]:
        """Roll back the most recently applied migration."""
        with self._engine.session() as sess:
            history = MigrationHistory(sess)
            history.ensure_table()
            applied = history.get_applied()
            if not applied:
                return None
            latest = applied[-1]
            migration = self._migrations.get(latest.version)
            if migration is None:
                raise MigrationNotFoundError(latest.version)
            runner = MigrationRunner(sess, validate_checksum=False)
            runner.rollback(migration)
            return latest

    def status(self) -> list[dict]:
        """Return status of all registered migrations."""
        with self._engine.session() as sess:
            history = MigrationHistory(sess)
            history.ensure_table()
            applied_map = {r.version: r for r in history.get_applied()}

        rows = []
        for version, migration in sorted(self._migrations.items()):
            rec = applied_map.get(version)
            rows.append({
                "version": version,
                "description": migration.description,
                "applied": rec is not None,
                "applied_at": rec.applied_at if rec else None,
                "duration_ms": rec.duration_ms if rec else None,
            })
        return rows

    def pending(self) -> list[Migration]:
        """Return migrations not yet applied."""
        with self._engine.session() as sess:
            history = MigrationHistory(sess)
            history.ensure_table()
            applied = {r.version for r in history.get_applied()}
        return [
            m for v, m in sorted(self._migrations.items())
            if v not in applied
        ]
