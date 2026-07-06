# IIOS Database Framework

Production-grade database layer for the Investment Intelligence Operating System.

## Architecture

```
iios/infrastructure/database/
├── database_constants.py       # Enums & numeric constants
├── database_exceptions.py      # Full exception hierarchy
├── database_config.py          # Dataclass configs (Pool, Cache, Audit, Backup, Migration)
├── database_connection.py      # Abstract + SQLite/PG/MySQL/DuckDB connections
├── database_session.py         # Session with transaction control, savepoints, stats
├── database_engine.py          # Engine: owns pool, sessions, metrics, cache
├── database_factory.py         # Factory helpers (sqlite, in_memory, postgresql, from_dict)
├── database_registry.py        # Named engine registry (get_database_registry)
├── database_context.py         # Thread-local ambient session context
├── database_manager.py         # Main façade (get_database_manager)
│
├── orm/
│   ├── specification.py        # Composable filter predicates (Eq, And, Or, In, ...)
│   ├── entity_mapper.py        # Row ↔ dataclass mapping
│   ├── base_model.py           # BaseModel with class-level CRUD
│   ├── model_registry.py       # Auto-registry of BaseModel subclasses
│   ├── query_builder.py        # OrmQueryBuilder fluent API
│   └── query_executor.py       # SQL executor with cache + metrics integration
│
├── migrations/
│   ├── migration_runner.py     # Applies/rolls back a single Migration
│   ├── migration_manager.py    # Orchestrates all migrations, tracks state
│   ├── migration_history.py    # _iios_migrations table CRUD
│   └── schema_version.py       # _iios_schema_version table tracking
│
├── indexing/
│   └── index_manager.py        # CREATE/DROP/LIST indexes
│
├── backup/
│   └── backup_manager.py       # Full backup via sqlite3.backup API + gzip
│
├── audit/
│   └── audit_logger.py         # Write to _iios_audit table
│
├── performance/
│   ├── connection_pool.py      # Thread-safe pool with overflow + health check
│   ├── query_cache.py          # LRU + TTL cache keyed by (sql, params)
│   └── metrics.py              # Per-query metrics, p50/p95/p99, slow query log
│
├── sqlite_backend.py           # PRESERVED: legacy low-level SQLite backend
├── query_builder.py            # PRESERVED: legacy low-level fluent SQL builder
└── __init__.py                 # Full public surface
```

## Quick Start

### Create an engine

```python
from iios.infrastructure.database import DatabaseFactory, DatabaseEngine as EngineType

# In-memory (tests)
engine = DatabaseFactory.in_memory()

# File-based SQLite
engine = DatabaseFactory.sqlite("data/trades.db", name="trades")

# From config
from iios.infrastructure.database import DatabaseConfig, DatabaseEngine as EngineType
cfg = DatabaseConfig(name="trades", engine=EngineType.SQLITE, url="data/trades.db")
engine = DatabaseFactory.create(cfg)
```

### Session and queries

```python
with engine.session() as sess:
    # DDL
    sess.execute("CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY, symbol TEXT, qty INTEGER)")

    # DML
    result = sess.execute("INSERT INTO trades (symbol, qty) VALUES (?, ?)", ("RELIANCE", 10))
    print(result.lastrowid)

    # SELECT
    rows = sess.query("SELECT * FROM trades WHERE symbol=?", ("RELIANCE",))

    # Paginated
    page, total = sess.query_paginated("SELECT * FROM trades", page=2, page_size=20)
```

### ORM / BaseModel

```python
from dataclasses import dataclass
from typing import ClassVar, Optional
from iios.infrastructure.database import BaseModel, Eq, Gt, DatabaseFactory

@dataclass
class Trade(BaseModel):
    __tablename__: ClassVar[str] = "trades"
    __primary_key__: ClassVar[str] = "id"
    __schema__: ClassVar[str] = """
        CREATE TABLE IF NOT EXISTS trades (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT    NOT NULL,
            qty    INTEGER NOT NULL DEFAULT 0
        )
    """
    id: Optional[int] = None
    symbol: str = ""
    qty: int = 0

engine = DatabaseFactory.in_memory()

with engine.session() as sess:
    Trade.create_table(sess)
    t = Trade(symbol="RELIANCE", qty=10).save(sess)   # INSERT
    t.qty = 20
    t.save(sess)                                        # UPDATE
    all_trades = Trade.find_all(sess, spec=Gt("qty", 5))
    page, total = Trade.paginate(sess, page=1, page_size=10)
    Trade.delete_all(sess, spec=Eq("symbol", "RELIANCE"))
```

### Specifications

```python
from iios.infrastructure.database import Eq, Ne, Gt, Ge, Lt, Le, In, Between, And, Or, Not

# Simple
spec = Eq("symbol", "RELIANCE")

# Composing with operators
spec = Eq("symbol", "RELIANCE") & Gt("qty", 5)
spec = Eq("symbol", "TCS") | Eq("symbol", "INFY")
spec = ~Eq("active", 0)

# Complex
spec = (
    In("exchange", ["NSE", "BSE"])
    & Between("price", 100, 500)
    & ~IsNull("open_interest")
)

sql_frag, params = spec.to_sql()
```

### OrmQueryBuilder

```python
from iios.infrastructure.database import OrmQueryBuilder, Gt

with engine.session() as sess:
    high_qty = (
        OrmQueryBuilder(Trade, sess)
        .filter(Gt("qty", 100))
        .order_by("qty DESC")
        .limit(10)
        .all()
    )
    count = OrmQueryBuilder(Trade, sess).filter(Eq("symbol", "RELIANCE")).count()
    page, total = OrmQueryBuilder(Trade, sess).paginate(page=1, page_size=20)
```

### Migrations

```python
from iios.infrastructure.database import Migration, MigrationManager

class CreateTradesTable(Migration):
    version = "0001"
    description = "Create trades table"

    def up(self):
        return [
            """CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                qty    INTEGER NOT NULL DEFAULT 0
            )"""
        ]

    def down(self):
        return ["DROP TABLE IF EXISTS trades"]

mgr = MigrationManager(engine)
mgr.register(CreateTradesTable())
applied = mgr.migrate()    # idempotent — skips already-applied

status = mgr.status()      # list of {"version", "applied", "applied_at", ...}
pending = mgr.pending()    # list of Migration not yet applied
```

### Global manager (singleton pattern)

```python
from iios.infrastructure.database import get_database_manager, DatabaseConfig, DatabaseEngine as EngineType

mgr = get_database_manager()
mgr.configure("trades", DatabaseConfig(
    name="trades", engine=EngineType.SQLITE, url="data/trades.db"
))

with mgr.session("trades") as sess:
    rows = sess.query("SELECT * FROM trades")

# One-shot helpers
mgr.execute("trades", "DELETE FROM trades WHERE qty < ?", (1,))
rows = mgr.query("trades", "SELECT * FROM trades")
```

### Backup

```python
from iios.infrastructure.database import BackupManager, BackupConfig

cfg = BackupConfig(backup_dir="data/backups", compress=True, retention_days=7)
mgr = BackupManager(db_path="data/trades.db", config=cfg)
record = mgr.backup()
mgr.restore(record.backup_path, target_path="data/trades_restored.db")
```

### Audit

```python
from iios.infrastructure.database import AuditLogger, AuditEntry, AuditAction

with engine.session() as sess:
    audit = AuditLogger(sess)
    audit.ensure_table()
    audit.log(AuditEntry(
        action=AuditAction.INSERT.value,
        table_name="trades",
        new_value={"symbol": "RELIANCE", "qty": 10},
    ))
    entries = audit.query(table_name="trades", limit=50)
```

## Backward Compatibility

`SQLiteBackend` and `QueryBuilder` (the original low-level modules) remain fully exported from `iios.infrastructure.database` and are not modified.

## Supported Engines

| Engine     | Status  | Driver       |
|------------|---------|--------------|
| SQLite     | ✅ Full | built-in     |
| PostgreSQL | 🔶 Stub | psycopg2     |
| MySQL      | 🔶 Stub | pymysql      |
| DuckDB     | 🔶 Stub | duckdb       |

Stubs raise `UnsupportedEngineError` with install instructions.

## Test Coverage

```
tests/unit/infrastructure/test_database_framework.py  105/105 tests pass
```

Classes tested:
- `TestDatabaseConnection` (6 tests)
- `TestDatabaseSession` (8 tests)
- `TestConnectionPool` (4 tests)
- `TestSpecifications` (14 tests)
- `TestEntityMapper` (6 tests)
- `TestBaseModelCRUD` (10 tests)
- `TestOrmQueryBuilder` (5 tests)
- `TestMigrations` (10 tests)
- `TestQueryCache` (6 tests)
- `TestAuditLogger` (3 tests)
- `TestBackupManager` (5 tests)
- `TestIndexManager` (4 tests)
- `TestDatabaseFactory` (4 tests)
- `TestDatabaseRegistry` (6 tests)
- `TestDatabaseManager` (7 tests)
- `TestDatabaseContext` (2 tests)
- `TestDatabaseMetrics` (4 tests)
