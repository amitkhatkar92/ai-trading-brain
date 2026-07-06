"""
iios/infrastructure/database/database_exceptions.py
====================================================
Exception hierarchy for the IIOS Database Framework.
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = [
    "DatabaseError",
    "ConnectionError",
    "ConnectionPoolExhausted",
    "ConnectionTimeoutError",
    "SessionError",
    "TransactionError",
    "DeadlockError",
    "SavepointError",
    "QueryError",
    "QueryTimeoutError",
    "IntegrityError",
    "DuplicateKeyError",
    "ForeignKeyError",
    "NotNullError",
    "MigrationError",
    "MigrationNotFoundError",
    "MigrationAlreadyAppliedError",
    "MigrationConflictError",
    "SchemaError",
    "ModelError",
    "MappingError",
    "EntityNotFoundError",
    "IndexError",
    "DatabaseIndexError",
    "BackupError",
    "RestoreError",
    "AuditError",
    "ConfigurationError",
    "EngineNotFoundError",
    "UnsupportedEngineError",
]


class DatabaseError(Exception):
    """Base exception for all IIOS database errors."""

    def __init__(
        self,
        message: str,
        code: str = "DB-000",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context = context or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.args[0]!r}, code={self.code!r})"


# ── Connection errors ─────────────────────────────────────────────────────────

class ConnectionError(DatabaseError):
    """Failed to establish or maintain a database connection."""

    def __init__(self, message: str = "Database connection failed", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-CON-001"), **kw)


class ConnectionPoolExhausted(ConnectionError):
    """All connections in the pool are in use."""

    def __init__(self, pool_size: int = 0, timeout: float = 0) -> None:
        super().__init__(
            f"Connection pool exhausted (size={pool_size}, timeout={timeout}s)",
            code="DB-CON-002",
            context={"pool_size": pool_size, "timeout": timeout},
        )


class ConnectionTimeoutError(ConnectionError):
    def __init__(self, timeout: float = 0) -> None:
        super().__init__(
            f"Connection timed out after {timeout}s",
            code="DB-CON-003",
            context={"timeout": timeout},
        )


# ── Session and transaction errors ───────────────────────────────────────────

class SessionError(DatabaseError):
    def __init__(self, message: str = "Session error", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-SES-001"), **kw)


class TransactionError(DatabaseError):
    def __init__(self, message: str = "Transaction error", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-TXN-001"), **kw)


class DeadlockError(TransactionError):
    def __init__(self, message: str = "Deadlock detected") -> None:
        super().__init__(message, code="DB-TXN-002")


class SavepointError(TransactionError):
    def __init__(self, savepoint: str = "") -> None:
        super().__init__(
            f"Savepoint operation failed: {savepoint!r}",
            code="DB-TXN-003",
            context={"savepoint": savepoint},
        )


# ── Query errors ─────────────────────────────────────────────────────────────

class QueryError(DatabaseError):
    def __init__(self, message: str = "Query execution failed", sql: str = "", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-QRY-001"), **kw)
        self.sql = sql

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.args[0]!r}, sql={self.sql[:80]!r})"


class QueryTimeoutError(QueryError):
    def __init__(self, timeout: float = 0, sql: str = "") -> None:
        super().__init__(
            f"Query timed out after {timeout}s",
            sql=sql,
            code="DB-QRY-002",
            context={"timeout": timeout},
        )


class IntegrityError(QueryError):
    def __init__(self, message: str = "Integrity constraint violated", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-QRY-010"), **kw)


class DuplicateKeyError(IntegrityError):
    def __init__(self, table: str = "", key: Any = None) -> None:
        super().__init__(
            f"Duplicate key in table '{table}': {key}",
            code="DB-QRY-011",
            context={"table": table, "key": str(key)},
        )


class ForeignKeyError(IntegrityError):
    def __init__(self, table: str = "", column: str = "") -> None:
        super().__init__(
            f"Foreign key violation: {table}.{column}",
            code="DB-QRY-012",
        )


class NotNullError(IntegrityError):
    def __init__(self, table: str = "", column: str = "") -> None:
        super().__init__(
            f"NOT NULL constraint failed: {table}.{column}",
            code="DB-QRY-013",
        )


# ── Migration errors ─────────────────────────────────────────────────────────

class MigrationError(DatabaseError):
    def __init__(self, message: str = "Migration failed", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-MIG-001"), **kw)


class MigrationNotFoundError(MigrationError):
    def __init__(self, version: str = "") -> None:
        super().__init__(
            f"Migration version '{version}' not found",
            code="DB-MIG-002",
            context={"version": version},
        )


class MigrationAlreadyAppliedError(MigrationError):
    def __init__(self, version: str = "") -> None:
        super().__init__(
            f"Migration '{version}' is already applied",
            code="DB-MIG-003",
            context={"version": version},
        )


class MigrationConflictError(MigrationError):
    def __init__(self, version: str = "") -> None:
        super().__init__(
            f"Migration version conflict at '{version}'",
            code="DB-MIG-004",
        )


# ── Schema / ORM errors ───────────────────────────────────────────────────────

class SchemaError(DatabaseError):
    def __init__(self, message: str = "Schema error", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-SCH-001"), **kw)


class ModelError(DatabaseError):
    def __init__(self, message: str = "Model error", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-ORM-001"), **kw)


class MappingError(ModelError):
    def __init__(self, model: str = "", field: str = "") -> None:
        super().__init__(
            f"Mapping error in model '{model}', field '{field}'",
            code="DB-ORM-002",
        )


class EntityNotFoundError(ModelError):
    def __init__(self, model: str = "", pk: Any = None) -> None:
        super().__init__(
            f"Entity '{model}' with pk={pk!r} not found",
            code="DB-ORM-003",
            context={"model": model, "pk": str(pk)},
        )


# ── Index errors ─────────────────────────────────────────────────────────────

class DatabaseIndexError(DatabaseError):
    def __init__(self, message: str = "Index error", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-IDX-001"), **kw)


# backward-compat alias (avoids shadowing builtins)
IndexError = DatabaseIndexError


# ── Backup / restore errors ───────────────────────────────────────────────────

class BackupError(DatabaseError):
    def __init__(self, message: str = "Backup failed", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-BAK-001"), **kw)


class RestoreError(BackupError):
    def __init__(self, message: str = "Restore failed", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-BAK-002"), **kw)


# ── Audit errors ─────────────────────────────────────────────────────────────

class AuditError(DatabaseError):
    def __init__(self, message: str = "Audit error", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-AUD-001"), **kw)


# ── Engine / config errors ────────────────────────────────────────────────────

class ConfigurationError(DatabaseError):
    def __init__(self, message: str = "Database configuration error", **kw: Any) -> None:
        super().__init__(message, code=kw.pop("code", "DB-CFG-001"), **kw)


class EngineNotFoundError(DatabaseError):
    def __init__(self, name: str = "") -> None:
        super().__init__(
            f"Database engine '{name}' not registered",
            code="DB-ENG-001",
            context={"name": name},
        )


class UnsupportedEngineError(DatabaseError):
    def __init__(self, engine: str = "") -> None:
        super().__init__(
            f"Database engine '{engine}' is not supported",
            code="DB-ENG-002",
            context={"engine": engine},
        )
