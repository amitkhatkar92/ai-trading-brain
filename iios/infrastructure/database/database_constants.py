"""
iios/infrastructure/database/database_constants.py
===================================================
Enumerations and constants for the IIOS Database Framework.
"""

from __future__ import annotations

from enum import Enum, auto

__all__ = [
    "DatabaseEngine",
    "TransactionIsolation",
    "IndexType",
    "MigrationStatus",
    "AuditAction",
    "QueryOperation",
    "BackupType",
    "ConnectionState",
    "SchemaChangeType",
    # Numeric constants
    "DEFAULT_POOL_SIZE",
    "DEFAULT_POOL_OVERFLOW",
    "DEFAULT_POOL_TIMEOUT",
    "DEFAULT_QUERY_CACHE_SIZE",
    "DEFAULT_QUERY_CACHE_TTL",
    "DEFAULT_MIGRATION_TABLE",
    "DEFAULT_AUDIT_TABLE",
    "DEFAULT_SCHEMA_VERSION_TABLE",
    "MAX_SAVEPOINTS",
    "DEFAULT_BACKUP_RETENTION",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_PAGE_SIZE",
    "MAX_QUERY_LENGTH",
]


class DatabaseEngine(str, Enum):
    """Supported database backends."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    DUCKDB = "duckdb"


class TransactionIsolation(str, Enum):
    """Transaction isolation levels."""
    READ_UNCOMMITTED = "READ UNCOMMITTED"
    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"
    DEFERRED = "DEFERRED"       # SQLite specific
    IMMEDIATE = "IMMEDIATE"     # SQLite specific
    EXCLUSIVE = "EXCLUSIVE"     # SQLite specific


class IndexType(str, Enum):
    """Database index types."""
    PRIMARY = "primary"
    UNIQUE = "unique"
    SECONDARY = "secondary"
    COMPOSITE = "composite"
    FULLTEXT = "fulltext"
    PARTIAL = "partial"


class MigrationStatus(str, Enum):
    """Migration execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class AuditAction(str, Enum):
    """Auditable database actions."""
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SELECT = "SELECT"
    SCHEMA_CHANGE = "SCHEMA_CHANGE"
    MIGRATION = "MIGRATION"
    BACKUP = "BACKUP"
    RESTORE = "RESTORE"
    CONNECT = "CONNECT"
    DISCONNECT = "DISCONNECT"
    TRANSACTION_BEGIN = "TRANSACTION_BEGIN"
    TRANSACTION_COMMIT = "TRANSACTION_COMMIT"
    TRANSACTION_ROLLBACK = "TRANSACTION_ROLLBACK"


class QueryOperation(str, Enum):
    """SQL query operation types."""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"
    DROP = "DROP"
    ALTER = "ALTER"
    INDEX = "INDEX"
    PRAGMA = "PRAGMA"


class BackupType(str, Enum):
    """Backup strategy types."""
    FULL = "full"
    INCREMENTAL = "incremental"
    SNAPSHOT = "snapshot"


class ConnectionState(str, Enum):
    """Connection lifecycle state."""
    IDLE = "idle"
    IN_USE = "in_use"
    CLOSED = "closed"
    ERROR = "error"


class SchemaChangeType(str, Enum):
    """Types of schema modifications."""
    CREATE_TABLE = "create_table"
    DROP_TABLE = "drop_table"
    ALTER_TABLE = "alter_table"
    ADD_COLUMN = "add_column"
    DROP_COLUMN = "drop_column"
    CREATE_INDEX = "create_index"
    DROP_INDEX = "drop_index"
    CREATE_VIEW = "create_view"
    DROP_VIEW = "drop_view"


# ── Numeric constants ─────────────────────────────────────────────────────────

DEFAULT_POOL_SIZE: int = 5
DEFAULT_POOL_OVERFLOW: int = 10
DEFAULT_POOL_TIMEOUT: float = 30.0
DEFAULT_QUERY_CACHE_SIZE: int = 500
DEFAULT_QUERY_CACHE_TTL: float = 60.0
DEFAULT_MIGRATION_TABLE: str = "_iios_migrations"
DEFAULT_AUDIT_TABLE: str = "_iios_audit"
DEFAULT_SCHEMA_VERSION_TABLE: str = "_iios_schema_version"
MAX_SAVEPOINTS: int = 16
DEFAULT_BACKUP_RETENTION: int = 7          # days
DEFAULT_BATCH_SIZE: int = 500
DEFAULT_PAGE_SIZE: int = 50
MAX_QUERY_LENGTH: int = 65_536
