"""
iios/infrastructure/database/__init__.py
=========================================
Public surface of the IIOS Database Framework.

Preserves backward-compatible exports (SQLiteBackend, QueryBuilder)
and adds the full new framework API.
"""

from __future__ import annotations

# ── Backward-compatible exports (MUST remain) ─────────────────────────────────
from .sqlite_backend import SQLiteBackend
from .query_builder import QueryBuilder

# ── Constants & exceptions ────────────────────────────────────────────────────
from .database_constants import (
    DatabaseEngine,
    TransactionIsolation,
    IndexType,
    MigrationStatus,
    AuditAction,
    QueryOperation,
    BackupType,
    ConnectionState,
    SchemaChangeType,
    DEFAULT_POOL_SIZE,
    DEFAULT_POOL_TIMEOUT,
    DEFAULT_QUERY_CACHE_SIZE,
    DEFAULT_QUERY_CACHE_TTL,
    DEFAULT_MIGRATION_TABLE,
    DEFAULT_AUDIT_TABLE,
    DEFAULT_SCHEMA_VERSION_TABLE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_PAGE_SIZE,
)
from .database_exceptions import (
    DatabaseError,
    ConnectionError,
    ConnectionPoolExhausted,
    ConnectionTimeoutError,
    SessionError,
    TransactionError,
    DeadlockError,
    SavepointError,
    QueryError,
    QueryTimeoutError,
    IntegrityError,
    DuplicateKeyError,
    ForeignKeyError,
    NotNullError,
    MigrationError,
    MigrationNotFoundError,
    MigrationAlreadyAppliedError,
    MigrationConflictError,
    SchemaError,
    ModelError,
    MappingError,
    EntityNotFoundError,
    BackupError,
    RestoreError,
    AuditError,
    ConfigurationError,
    EngineNotFoundError,
    UnsupportedEngineError,
)

# ── Configuration ─────────────────────────────────────────────────────────────
from .database_config import (
    PoolConfig,
    CacheConfig,
    AuditConfig,
    BackupConfig,
    MigrationConfig,
    DatabaseConfig,
)

# ── Core ──────────────────────────────────────────────────────────────────────
from .database_connection import DatabaseConnection, Cursor, Row, create_connection
from .database_session import DatabaseSession, SessionStats, ExecuteResult
from .database_engine import DatabaseEngine as Engine
from .database_factory import DatabaseFactory
from .database_registry import DatabaseRegistry, get_database_registry, reset_database_registry
from .database_context import DatabaseContext, current_session, with_session
from .database_manager import DatabaseManager, get_database_manager, reset_database_manager

# ── ORM ───────────────────────────────────────────────────────────────────────
from .orm import (
    Specification,
    Eq, Ne, Gt, Ge, Lt, Le,
    Like, ILike, In, NotIn,
    IsNull, IsNotNull,
    Between,
    And, Or, Not,
    Always, Never,
    EntityMapper,
    BaseModel,
    ModelRegistry, get_model_registry, reset_model_registry,
    OrmQueryBuilder,
    QueryExecutor,
)

# ── Migrations ────────────────────────────────────────────────────────────────
from .migrations import (
    Migration, MigrationRunner,
    MigrationHistory, MigrationRecord,
    MigrationManager,
    SchemaVersion, SchemaVersionTracker,
)

# ── Indexing ──────────────────────────────────────────────────────────────────
from .indexing import IndexDefinition, IndexManager

# ── Backup ────────────────────────────────────────────────────────────────────
from .backup import BackupRecord, BackupManager

# ── Audit ─────────────────────────────────────────────────────────────────────
from .audit import AuditEntry, AuditLogger

# ── Performance ───────────────────────────────────────────────────────────────
from .performance import (
    ConnectionPool, PoolStats,
    QueryCache, CacheStats,
    DatabaseMetrics, QueryMetric,
)

__all__ = [
    # Backward compat
    "SQLiteBackend", "QueryBuilder",

    # Constants
    "DatabaseEngine", "TransactionIsolation", "IndexType", "MigrationStatus",
    "AuditAction", "QueryOperation", "BackupType", "ConnectionState", "SchemaChangeType",
    "DEFAULT_POOL_SIZE", "DEFAULT_POOL_TIMEOUT", "DEFAULT_QUERY_CACHE_SIZE",
    "DEFAULT_QUERY_CACHE_TTL", "DEFAULT_MIGRATION_TABLE", "DEFAULT_AUDIT_TABLE",
    "DEFAULT_SCHEMA_VERSION_TABLE", "DEFAULT_BATCH_SIZE", "DEFAULT_PAGE_SIZE",

    # Exceptions
    "DatabaseError", "ConnectionError", "ConnectionPoolExhausted", "ConnectionTimeoutError",
    "SessionError", "TransactionError", "DeadlockError", "SavepointError",
    "QueryError", "QueryTimeoutError", "IntegrityError", "DuplicateKeyError",
    "ForeignKeyError", "NotNullError", "MigrationError", "MigrationNotFoundError",
    "MigrationAlreadyAppliedError", "MigrationConflictError",
    "SchemaError", "ModelError", "MappingError", "EntityNotFoundError",
    "BackupError", "RestoreError", "AuditError",
    "ConfigurationError", "EngineNotFoundError", "UnsupportedEngineError",

    # Config
    "PoolConfig", "CacheConfig", "AuditConfig", "BackupConfig",
    "MigrationConfig", "DatabaseConfig",

    # Core
    "DatabaseConnection", "Cursor", "Row", "create_connection",
    "DatabaseSession", "SessionStats", "ExecuteResult",
    "Engine", "DatabaseFactory",
    "DatabaseRegistry", "get_database_registry", "reset_database_registry",
    "DatabaseContext", "current_session", "with_session",
    "DatabaseManager", "get_database_manager", "reset_database_manager",

    # ORM
    "Specification",
    "Eq", "Ne", "Gt", "Ge", "Lt", "Le",
    "Like", "ILike", "In", "NotIn",
    "IsNull", "IsNotNull", "Between",
    "And", "Or", "Not", "Always", "Never",
    "EntityMapper", "BaseModel",
    "ModelRegistry", "get_model_registry", "reset_model_registry",
    "OrmQueryBuilder", "QueryExecutor",

    # Migrations
    "Migration", "MigrationRunner",
    "MigrationHistory", "MigrationRecord",
    "MigrationManager",
    "SchemaVersion", "SchemaVersionTracker",

    # Indexing
    "IndexDefinition", "IndexManager",

    # Backup
    "BackupRecord", "BackupManager",

    # Audit
    "AuditEntry", "AuditLogger",

    # Performance
    "ConnectionPool", "PoolStats",
    "QueryCache", "CacheStats",
    "DatabaseMetrics", "QueryMetric",
]

