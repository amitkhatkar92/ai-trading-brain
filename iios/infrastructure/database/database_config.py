"""
iios/infrastructure/database/database_config.py
================================================
Configuration dataclasses for the IIOS Database Framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .database_constants import (
    DatabaseEngine,
    TransactionIsolation,
    DEFAULT_POOL_SIZE,
    DEFAULT_POOL_OVERFLOW,
    DEFAULT_POOL_TIMEOUT,
    DEFAULT_QUERY_CACHE_SIZE,
    DEFAULT_QUERY_CACHE_TTL,
    DEFAULT_PAGE_SIZE,
    DEFAULT_BATCH_SIZE,
)

__all__ = [
    "DatabaseConfig",
    "PoolConfig",
    "CacheConfig",
    "AuditConfig",
    "BackupConfig",
    "MigrationConfig",
]


@dataclass
class PoolConfig:
    """Connection pool configuration."""
    size: int = DEFAULT_POOL_SIZE
    max_overflow: int = DEFAULT_POOL_OVERFLOW
    timeout: float = DEFAULT_POOL_TIMEOUT
    recycle: float = 3600.0          # recycle connections older than N seconds
    pre_ping: bool = True             # health-check connections before use
    echo: bool = False                # log pool events


@dataclass
class CacheConfig:
    """Query result cache configuration."""
    enabled: bool = True
    max_size: int = DEFAULT_QUERY_CACHE_SIZE
    ttl: float = DEFAULT_QUERY_CACHE_TTL
    cache_selects: bool = True
    exclude_tables: list[str] = field(default_factory=list)


@dataclass
class AuditConfig:
    """Audit logging configuration."""
    enabled: bool = True
    track_selects: bool = False      # SELECT queries are high-volume; opt-in
    track_schema_changes: bool = True
    track_migrations: bool = True
    track_transactions: bool = False
    max_history: int = 100_000
    retain_days: int = 90


@dataclass
class BackupConfig:
    """Backup configuration."""
    enabled: bool = True
    backup_dir: str = "data/backups"
    retention_days: int = 7
    compress: bool = True
    auto_backup: bool = False          # if True, backup on engine close
    pre_migration_backup: bool = True  # backup before running migrations


@dataclass
class MigrationConfig:
    """Migration system configuration."""
    auto_migrate: bool = False         # run pending migrations on startup
    allow_downgrade: bool = True
    validate_checksum: bool = True     # reject modified migration scripts
    scan_packages: list[str] = field(default_factory=list)


@dataclass
class DatabaseConfig:
    """Complete database engine configuration.

    Usage::

        cfg = DatabaseConfig(
            name="trades_db",
            engine=DatabaseEngine.SQLITE,
            url="data/trades.db",
        )
        engine = DatabaseFactory.create(cfg)
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    name: str = "default"
    engine: DatabaseEngine = DatabaseEngine.SQLITE

    # ── Connection URL ────────────────────────────────────────────────────────
    # SQLite:     "path/to/file.db"  or  ":memory:"
    # PostgreSQL: "host:5432/dbname"
    # MySQL:      "host:3306/dbname"
    # DuckDB:     "path/to/file.ddb"  or  ":memory:"
    url: str = ":memory:"

    # ── Auth (ignored for SQLite / DuckDB) ───────────────────────────────────
    username: str = ""
    password: str = ""
    database: str = ""
    schema: str = ""

    # ── Behaviour ─────────────────────────────────────────────────────────────
    isolation: TransactionIsolation = TransactionIsolation.DEFERRED
    echo: bool = False               # log all SQL statements
    check_same_thread: bool = False  # SQLite only
    timeout: float = 30.0
    busy_timeout: int = 5000         # SQLite busy_timeout ms
    wal_mode: bool = True            # SQLite WAL mode (much better concurrency)
    foreign_keys: bool = True

    # ── Sub-configurations ────────────────────────────────────────────────────
    pool: PoolConfig = field(default_factory=PoolConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    audit: AuditConfig = field(default_factory=AuditConfig)
    backup: BackupConfig = field(default_factory=BackupConfig)
    migrations: MigrationConfig = field(default_factory=MigrationConfig)

    # ── Pagination defaults ───────────────────────────────────────────────────
    default_page_size: int = DEFAULT_PAGE_SIZE
    default_batch_size: int = DEFAULT_BATCH_SIZE

    # ── Extra driver kwargs ───────────────────────────────────────────────────
    extra: dict[str, Any] = field(default_factory=dict)

    def to_connect_url(self) -> str:
        """Build a driver-appropriate connection string."""
        if self.engine == DatabaseEngine.SQLITE:
            return self.url
        if self.engine == DatabaseEngine.POSTGRESQL:
            auth = f"{self.username}:{self.password}@" if self.username else ""
            db = f"/{self.database}" if self.database else ""
            return f"postgresql://{auth}{self.url}{db}"
        if self.engine == DatabaseEngine.MYSQL:
            auth = f"{self.username}:{self.password}@" if self.username else ""
            db = f"/{self.database}" if self.database else ""
            return f"mysql://{auth}{self.url}{db}"
        if self.engine == DatabaseEngine.DUCKDB:
            return self.url
        return self.url
