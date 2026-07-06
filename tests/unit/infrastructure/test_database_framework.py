"""
tests/unit/infrastructure/test_database_framework.py
=====================================================
Comprehensive tests for the IIOS Database Framework.
Target: 90%+ coverage across all database/ subpackages.
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import ClassVar, Optional

import pytest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

from iios.infrastructure.database import (
    # Constants
    DatabaseEngine as EngineType,
    MigrationStatus,
    AuditAction,
    IndexType,
    BackupType,
    ConnectionState,
    # Exceptions
    DatabaseError,
    ConnectionPoolExhausted,
    SessionError,
    TransactionError,
    SavepointError,
    MigrationError,
    MigrationConflictError,
    MigrationNotFoundError,
    EngineNotFoundError,
    ConfigurationError,
    # Config
    PoolConfig,
    CacheConfig,
    AuditConfig,
    BackupConfig,
    DatabaseConfig,
    # Core
    create_connection,
    DatabaseSession,
    SessionStats,
    ExecuteResult,
    # Engine / factory / registry
    Engine,
    DatabaseFactory,
    DatabaseRegistry,
    get_database_registry,
    reset_database_registry,
    DatabaseManager,
    get_database_manager,
    reset_database_manager,
    # Context
    DatabaseContext,
    current_session,
    with_session,
    # ORM
    Eq, Ne, Gt, Ge, Lt, Le,
    Like, ILike, In, NotIn,
    IsNull, IsNotNull,
    Between, And, Or, Not,
    Always, Never,
    Specification,
    EntityMapper,
    BaseModel,
    ModelRegistry,
    get_model_registry,
    reset_model_registry,
    OrmQueryBuilder,
    # Migrations
    Migration,
    MigrationRunner,
    MigrationHistory,
    MigrationManager,
    SchemaVersionTracker,
    # Indexing
    IndexDefinition,
    IndexManager,
    # Backup
    BackupManager,
    # Audit
    AuditEntry,
    AuditLogger,
    # Performance
    ConnectionPool,
    QueryCache,
    DatabaseMetrics,
)


def make_config(url: str = ":memory:", name: str = "test") -> DatabaseConfig:
    return DatabaseConfig(
        name=name,
        engine=EngineType.SQLITE,
        url=url,
        pool=PoolConfig(size=2, max_overflow=2),
        cache=CacheConfig(enabled=True, ttl=30.0),
        audit=AuditConfig(enabled=False),
    )


def make_engine(url: str = ":memory:", name: str = "test") -> Engine:
    return DatabaseFactory.create(make_config(url, name))


def make_in_memory() -> Engine:
    return DatabaseFactory.in_memory(name="test")


# ---------------------------------------------------------------------------
# 1. DatabaseConnection
# ---------------------------------------------------------------------------

class TestDatabaseConnection:
    def test_sqlite_connect_and_close(self):
        cfg = make_config()
        conn = create_connection(cfg)
        assert conn.state == ConnectionState.IDLE
        conn.open()
        cursor = conn.execute("SELECT 1 AS val")
        rows = cursor.fetchall()
        assert rows[0]["val"] == 1
        conn.close()

    def test_sqlite_transaction(self):
        cfg = make_config()
        conn = create_connection(cfg)
        conn.open()
        conn.execute(
            "CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)"
        )
        conn.begin()
        conn.execute("INSERT INTO t VALUES (1, 'hello')")
        conn.commit()
        cursor = conn.execute("SELECT COUNT(*) AS cnt FROM t")
        assert cursor.fetchone()["cnt"] == 1
        conn.close()

    def test_sqlite_rollback(self):
        cfg = make_config()
        conn = create_connection(cfg)
        conn.open()
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        conn.begin()
        conn.execute("INSERT INTO t VALUES (1, 'x')")
        conn.rollback()
        cursor = conn.execute("SELECT COUNT(*) AS cnt FROM t")
        assert cursor.fetchone()["cnt"] == 0
        conn.close()

    def test_savepoint(self):
        cfg = make_config()
        conn = create_connection(cfg)
        conn.open()
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        conn.begin()
        conn.execute("INSERT INTO t VALUES (1, 'outer')")
        conn.savepoint("sp1")
        conn.execute("INSERT INTO t VALUES (2, 'inner')")
        conn.rollback_to("sp1")
        conn.release_savepoint("sp1")
        conn.commit()
        cursor = conn.execute("SELECT COUNT(*) AS cnt FROM t")
        assert cursor.fetchone()["cnt"] == 1
        conn.close()

    def test_query_and_query_one(self):
        cfg = make_config()
        conn = create_connection(cfg)
        conn.open()
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        conn.begin()
        conn.execute("INSERT INTO t VALUES (1, 'a')")
        conn.execute("INSERT INTO t VALUES (2, 'b')")
        conn.commit()
        rows = conn.query("SELECT * FROM t ORDER BY id")
        assert len(rows) == 2
        one = conn.query_one("SELECT * FROM t WHERE id=?", (1,))
        assert one["v"] == "a"
        conn.close()

    def test_query_count(self):
        cfg = make_config()
        conn = create_connection(cfg)
        conn.open()
        conn.execute("SELECT 1")
        conn.execute("SELECT 1")
        assert conn.query_count == 2
        conn.close()


# ---------------------------------------------------------------------------
# 2. DatabaseSession
# ---------------------------------------------------------------------------

class TestDatabaseSession:
    def test_session_context_manager_commit(self):
        engine = make_in_memory()
        with engine.session() as sess:
            sess.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
            sess.execute("INSERT INTO t VALUES (1, 'hello')")
        with engine.session() as sess:
            row = sess.query_one("SELECT v FROM t WHERE id=1")
            assert row["v"] == "hello"
        engine.close()

    def test_session_context_manager_rollback_on_error(self):
        engine = make_in_memory()
        with engine.session() as sess:
            sess.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        with pytest.raises(Exception):
            with engine.session() as sess:
                sess.execute("INSERT INTO t VALUES (1, 'x')")
                raise RuntimeError("intentional")
        with engine.session() as sess:
            count = sess.query_scalar("SELECT COUNT(*) FROM t")
            assert count == 0
        engine.close()

    def test_session_savepoint(self):
        engine = make_in_memory()
        with engine.session() as sess:
            sess.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
            try:
                with sess.savepoint("sp1"):
                    sess.execute("INSERT INTO t VALUES (1, 'will roll back')")
                    raise ValueError("trigger rollback")
            except ValueError:
                pass
            sess.execute("INSERT INTO t VALUES (2, 'ok')")
        with engine.session() as sess:
            rows = sess.query("SELECT * FROM t")
            assert len(rows) == 1
            assert rows[0]["id"] == 2
        engine.close()

    def test_query_paginated(self):
        engine = make_in_memory()
        with engine.session() as sess:
            sess.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
            for i in range(10):
                sess.execute("INSERT INTO t VALUES (?, ?)", (i + 1, f"v{i}"))
        with engine.session() as sess:
            rows, total = sess.query_paginated("SELECT * FROM t ORDER BY id", page=2, page_size=3)
            assert total == 10
            assert len(rows) == 3
            assert rows[0]["id"] == 4
        engine.close()

    def test_query_scalar(self):
        engine = make_in_memory()
        with engine.session() as sess:
            sess.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
            sess.execute("INSERT INTO t VALUES (42)")
        with engine.session() as sess:
            val = sess.query_scalar("SELECT id FROM t")
            assert val == 42
        engine.close()

    def test_table_exists(self):
        engine = make_in_memory()
        with engine.session() as sess:
            assert not sess.table_exists("nothere")
            sess.execute("CREATE TABLE nothere (id INTEGER PRIMARY KEY)")
            assert sess.table_exists("nothere")
        engine.close()

    def test_execute_result(self):
        engine = make_in_memory()
        with engine.session() as sess:
            sess.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
            result = sess.execute("INSERT INTO t VALUES (1, 'hi')")
            assert isinstance(result, ExecuteResult)
            assert result.rowcount == 1
            assert result.lastrowid is not None
        engine.close()

    def test_stats_accumulate(self):
        engine = make_in_memory()
        with engine.session() as sess:
            sess.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        with engine.session() as sess:
            sess.execute("INSERT INTO t VALUES (1)")
            sess.query("SELECT * FROM t")
            stats = sess.stats
            assert stats.queries_executed >= 2
        engine.close()


# ---------------------------------------------------------------------------
# 3. ConnectionPool
# ---------------------------------------------------------------------------

class TestConnectionPool:
    def test_basic_checkout_checkin(self):
        cfg = make_config()
        pool = ConnectionPool(cfg)
        conn = pool.checkout()
        assert conn is not None
        pool.checkin(conn)
        pool.close_all()

    def test_pool_stats(self):
        cfg = make_config()
        pool = ConnectionPool(cfg)
        conn = pool.checkout()
        pool.checkin(conn)
        stats = pool.stats
        assert stats.total_checkouts == 1
        assert stats.total_checkins == 1
        pool.close_all()

    def test_pool_exhaustion(self):
        cfg = DatabaseConfig(
            name="tiny",
            engine=EngineType.SQLITE,
            url=":memory:",
            pool=PoolConfig(size=1, max_overflow=0, timeout=0.1),
        )
        pool = ConnectionPool(cfg)
        c1 = pool.checkout()
        with pytest.raises(ConnectionPoolExhausted):
            pool.checkout(timeout=0.05)
        pool.checkin(c1)
        pool.close_all()

    def test_concurrent_checkout(self):
        cfg = DatabaseConfig(
            name="conc",
            engine=EngineType.SQLITE,
            url=":memory:",
            pool=PoolConfig(size=3, max_overflow=3, timeout=5.0),
        )
        pool = ConnectionPool(cfg)
        results = []
        errors = []

        def worker():
            try:
                conn = pool.checkout()
                time.sleep(0.01)
                pool.checkin(conn)
                results.append(True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        assert len(results) == 6
        pool.close_all()


# ---------------------------------------------------------------------------
# 4. ORM – Specifications
# ---------------------------------------------------------------------------

class TestSpecifications:
    def test_eq(self):
        sql, params = Eq("col", "val").to_sql()
        assert "col = ?" in sql
        assert params == ["val"]

    def test_ne(self):
        sql, params = Ne("col", 1).to_sql()
        assert "!=" in sql

    def test_gt_ge_lt_le(self):
        for cls, op in [(Gt, ">"), (Ge, ">="), (Lt, "<"), (Le, "<=")]:
            sql, _ = cls("x", 5).to_sql()
            assert op in sql

    def test_like(self):
        sql, params = Like("name", "%foo%").to_sql()
        assert "LIKE" in sql.upper()
        assert params == ["%foo%"]

    def test_ilike(self):
        sql, params = ILike("name", "FOO%").to_sql()
        assert "LOWER" in sql
        assert params[0] == "foo%"

    def test_in(self):
        sql, params = In("col", [1, 2, 3]).to_sql()
        assert "IN" in sql
        assert params == [1, 2, 3]

    def test_in_empty(self):
        sql, params = In("col", []).to_sql()
        assert "1=0" in sql

    def test_not_in(self):
        sql, params = NotIn("col", [1, 2]).to_sql()
        assert "NOT IN" in sql

    def test_not_in_empty(self):
        sql, params = NotIn("col", []).to_sql()
        assert "1=1" in sql

    def test_is_null_is_not_null(self):
        s, _ = IsNull("col").to_sql()
        assert "IS NULL" in s
        s, _ = IsNotNull("col").to_sql()
        assert "IS NOT NULL" in s

    def test_between(self):
        sql, params = Between("col", 10, 20).to_sql()
        assert "BETWEEN" in sql
        assert params == [10, 20]

    def test_and(self):
        spec = Eq("a", 1) & Eq("b", 2)
        sql, params = spec.to_sql()
        assert "AND" in sql
        assert len(params) == 2

    def test_or(self):
        spec = Eq("a", 1) | Eq("a", 2)
        sql, params = spec.to_sql()
        assert "OR" in sql

    def test_not(self):
        spec = ~Eq("a", 1)
        sql, params = spec.to_sql()
        assert "NOT" in sql

    def test_always_never(self):
        sql, _ = Always().to_sql()
        assert "1=1" in sql
        sql, _ = Never().to_sql()
        assert "1=0" in sql

    def test_complex_chain(self):
        spec = (
            Eq("symbol", "RELIANCE")
            & Gt("price", 2000)
            & Le("price", 3000)
            & In("exchange", ["NSE", "BSE"])
        )
        sql, params = spec.to_sql()
        assert "AND" in sql
        assert len(params) == 5  # 1 + 1 + 1 + 2


# ---------------------------------------------------------------------------
# 5. ORM – EntityMapper
# ---------------------------------------------------------------------------

@dataclass
class _Widget(BaseModel):
    __tablename__: ClassVar[str] = "widgets"
    __primary_key__: ClassVar[str] = "id"
    __schema__: ClassVar[str] = """
        CREATE TABLE IF NOT EXISTS widgets (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT    NOT NULL DEFAULT '',
            value INTEGER NOT NULL DEFAULT 0
        )
    """
    id: Optional[int] = None
    name: str = ""
    value: int = 0


class TestEntityMapper:
    def test_to_row(self):
        w = _Widget(id=1, name="foo", value=42)
        row = EntityMapper.to_row(w)
        assert row == {"id": 1, "name": "foo", "value": 42}

    def test_from_row(self):
        row = {"id": 5, "name": "bar", "value": 99}
        w = EntityMapper.from_row(_Widget, row)
        assert isinstance(w, _Widget)
        assert w.name == "bar"

    def test_get_columns(self):
        cols = EntityMapper.get_columns(_Widget)
        assert "id" in cols and "name" in cols and "value" in cols

    def test_insert_sql(self):
        sql, cols = EntityMapper.get_insert_sql(_Widget)
        assert "INSERT INTO widgets" in sql
        assert "id" not in cols  # excluded when pk is None

    def test_update_sql(self):
        sql, cols, pk_val = EntityMapper.get_update_sql(_Widget, pk_value=3)
        assert "UPDATE widgets" in sql
        assert "WHERE id = ?" in sql
        assert pk_val == 3

    def test_non_dataclass_raises(self):
        with pytest.raises(TypeError):
            EntityMapper.to_row(object())


# ---------------------------------------------------------------------------
# 6. ORM – BaseModel CRUD
# ---------------------------------------------------------------------------

class TestBaseModelCRUD:
    @pytest.fixture(autouse=True)
    def engine(self):
        eng = make_in_memory()
        with eng.session() as sess:
            _Widget.create_table(sess)
        yield eng
        eng.close()

    def test_insert_assigns_id(self, engine):
        with engine.session() as sess:
            w = _Widget(name="alpha", value=1)
            w = w.save(sess)
            assert w.id is not None and w.id > 0

    def test_update(self, engine):
        with engine.session() as sess:
            w = _Widget(name="beta", value=10)
            w = w.save(sess)
            w.value = 99
            w.save(sess)
        with engine.session() as sess:
            found = _Widget.find_by_id(sess, w.id)
            assert found.value == 99

    def test_delete(self, engine):
        with engine.session() as sess:
            w = _Widget(name="gamma", value=5).save(sess)
            wid = w.id
        with engine.session() as sess:
            w = _Widget.find_by_id(sess, wid)
            ok = w.delete(sess)
            assert ok
        with engine.session() as sess:
            assert _Widget.find_by_id(sess, wid) is None

    def test_find_all(self, engine):
        with engine.session() as sess:
            for i in range(5):
                _Widget(name=f"w{i}", value=i).save(sess)
        with engine.session() as sess:
            all_w = _Widget.find_all(sess)
            assert len(all_w) == 5

    def test_find_all_with_spec(self, engine):
        with engine.session() as sess:
            for i in range(5):
                _Widget(name=f"w{i}", value=i).save(sess)
        with engine.session() as sess:
            big = _Widget.find_all(sess, spec=Gt("value", 2))
            assert all(w.value > 2 for w in big)

    def test_find_one(self, engine):
        with engine.session() as sess:
            _Widget(name="only", value=777).save(sess)
        with engine.session() as sess:
            w = _Widget.find_one(sess, Eq("name", "only"))
            assert w is not None
            assert w.value == 777

    def test_count(self, engine):
        with engine.session() as sess:
            for i in range(3):
                _Widget(name=f"c{i}", value=i).save(sess)
        with engine.session() as sess:
            assert _Widget.count(sess) == 3
            assert _Widget.count(sess, spec=Eq("value", 0)) == 1

    def test_exists(self, engine):
        with engine.session() as sess:
            _Widget(name="exists_check", value=42).save(sess)
        with engine.session() as sess:
            assert _Widget.exists(sess, Eq("name", "exists_check"))
            assert not _Widget.exists(sess, Eq("name", "ghost"))

    def test_delete_all(self, engine):
        with engine.session() as sess:
            for i in range(4):
                _Widget(name=f"d{i}", value=i).save(sess)
        with engine.session() as sess:
            deleted = _Widget.delete_all(sess, spec=Le("value", 1))
            assert deleted == 2

    def test_paginate(self, engine):
        with engine.session() as sess:
            for i in range(10):
                _Widget(name=f"p{i}", value=i).save(sess)
        with engine.session() as sess:
            page, total = _Widget.paginate(sess, page=2, page_size=3)
            assert total == 10
            assert len(page) == 3


# ---------------------------------------------------------------------------
# 7. OrmQueryBuilder
# ---------------------------------------------------------------------------

class TestOrmQueryBuilder:
    @pytest.fixture(autouse=True)
    def engine(self):
        eng = make_in_memory()
        with eng.session() as sess:
            _Widget.create_table(sess)
            for i in range(5):
                _Widget(name=f"q{i}", value=i * 10).save(sess)
        yield eng
        eng.close()

    def test_filter_limit_all(self, engine):
        with engine.session() as sess:
            results = (
                OrmQueryBuilder(_Widget, sess)
                .filter(Gt("value", 10))
                .limit(2)
                .all()
            )
            assert len(results) == 2
            assert all(w.value > 10 for w in results)

    def test_count(self, engine):
        with engine.session() as sess:
            n = OrmQueryBuilder(_Widget, sess).filter(Le("value", 20)).count()
            assert n == 3  # 0, 10, 20

    def test_one(self, engine):
        with engine.session() as sess:
            w = OrmQueryBuilder(_Widget, sess).filter(Eq("name", "q0")).one()
            assert w is not None
            assert w.value == 0

    def test_delete(self, engine):
        with engine.session() as sess:
            deleted = OrmQueryBuilder(_Widget, sess).filter(Gt("value", 30)).delete()
            assert deleted == 1  # only value=40

    def test_paginate(self, engine):
        with engine.session() as sess:
            page, total = OrmQueryBuilder(_Widget, sess).paginate(page=1, page_size=2)
            assert total == 5
            assert len(page) == 2


# ---------------------------------------------------------------------------
# 8. Migrations
# ---------------------------------------------------------------------------

class CreateAlphaTable(Migration):
    version = "0001"
    description = "Create alpha table"

    def up(self):
        return [
            "CREATE TABLE IF NOT EXISTS alpha (id INTEGER PRIMARY KEY, v TEXT)"
        ]

    def down(self):
        return ["DROP TABLE IF EXISTS alpha"]


class AddBetaTable(Migration):
    version = "0002"
    description = "Create beta table"

    def up(self):
        return [
            "CREATE TABLE IF NOT EXISTS beta (id INTEGER PRIMARY KEY, name TEXT)"
        ]

    def down(self):
        return ["DROP TABLE IF EXISTS beta"]


class TestMigrations:
    @pytest.fixture()
    def engine(self):
        eng = make_in_memory()
        yield eng
        eng.close()

    def test_apply_migration(self, engine):
        with engine.session() as sess:
            runner = MigrationRunner(sess)
            rec = runner.apply(CreateAlphaTable())
            assert rec.status == MigrationStatus.COMPLETED.value

    def test_idempotent_apply(self, engine):
        with engine.session() as sess:
            runner = MigrationRunner(sess)
            runner.apply(CreateAlphaTable())
            rec = runner.apply(CreateAlphaTable())  # again — should skip
            assert rec.status == MigrationStatus.COMPLETED.value

    def test_rollback(self, engine):
        with engine.session() as sess:
            runner = MigrationRunner(sess)
            runner.apply(CreateAlphaTable())
            ok = runner.rollback(CreateAlphaTable())
            assert ok

    def test_migration_manager_migrate(self, engine):
        mgr = MigrationManager(engine)
        mgr.register_many(CreateAlphaTable(), AddBetaTable())
        applied = mgr.migrate()
        assert len(applied) == 2
        assert all(r.status == MigrationStatus.COMPLETED.value for r in applied)

    def test_migration_manager_idempotent(self, engine):
        mgr = MigrationManager(engine)
        mgr.register(CreateAlphaTable())
        mgr.migrate()
        applied = mgr.migrate()
        assert len(applied) == 0  # already applied

    def test_migration_status(self, engine):
        mgr = MigrationManager(engine)
        mgr.register(CreateAlphaTable())
        mgr.migrate()
        status = mgr.status()
        assert len(status) == 1
        assert status[0]["applied"] is True

    def test_pending(self, engine):
        mgr = MigrationManager(engine)
        mgr.register_many(CreateAlphaTable(), AddBetaTable())
        mgr.migrate()
        pending = mgr.pending()
        assert len(pending) == 0

    def test_rollback_last(self, engine):
        mgr = MigrationManager(engine)
        mgr.register_many(CreateAlphaTable(), AddBetaTable())
        mgr.migrate()
        rec = mgr.rollback_last()
        assert rec is not None
        assert rec.version == "0002"

    def test_migration_history(self, engine):
        with engine.session() as sess:
            history = MigrationHistory(sess)
            history.ensure_table()
            assert history.get_applied() == []
            runner = MigrationRunner(sess)
            runner.apply(CreateAlphaTable())
            assert history.is_applied("0001")
            assert not history.is_applied("0099")

    def test_schema_version_tracker(self, engine):
        with engine.session() as sess:
            tracker = SchemaVersionTracker(sess)
            tracker.ensure_table()
            assert tracker.get_current() is None
            tracker.set_version("1.0.0")
            assert tracker.get_current() == "1.0.0"
            tracker.set_version("1.1.0")
            assert tracker.get_current() == "1.1.0"


# ---------------------------------------------------------------------------
# 9. QueryCache
# ---------------------------------------------------------------------------

class TestQueryCache:
    def test_cache_miss_then_hit(self):
        cache = QueryCache(max_size=10, default_ttl=10.0)
        rows = [{"id": 1}]
        assert cache.get("SELECT 1", ()) is None
        cache.set("SELECT 1", (), rows)
        cached = cache.get("SELECT 1", ())
        assert cached == rows

    def test_cache_expiry(self):
        cache = QueryCache(max_size=10, default_ttl=0.05)
        cache.set("SELECT X", (), [{"x": 1}])
        time.sleep(0.1)
        assert cache.get("SELECT X", ()) is None

    def test_invalidate_table(self):
        cache = QueryCache(max_size=10)
        cache.set("SELECT * FROM trades", (), [{"id": 1}], tables=["trades"])
        cache.set("SELECT * FROM other", (), [{"id": 2}], tables=["other"])
        n = cache.invalidate_table("trades")
        assert n == 1
        assert cache.get("SELECT * FROM trades", ()) is None
        assert cache.get("SELECT * FROM other", ()) is not None

    def test_eviction(self):
        cache = QueryCache(max_size=3)
        for i in range(4):
            cache.set(f"SELECT {i}", (), [{"i": i}])
        assert cache.size == 3

    def test_stats(self):
        cache = QueryCache()
        cache.get("Q", ())
        cache.set("Q", (), [{}])
        cache.get("Q", ())
        stats = cache.stats
        assert stats.misses == 1
        assert stats.hits == 1

    def test_purge_expired(self):
        cache = QueryCache(default_ttl=0.05)
        cache.set("Q1", (), [{}])
        cache.set("Q2", (), [{}])
        time.sleep(0.1)
        n = cache.purge_expired()
        assert n == 2


# ---------------------------------------------------------------------------
# 10. AuditLogger
# ---------------------------------------------------------------------------

class TestAuditLogger:
    @pytest.fixture()
    def engine(self):
        eng = make_in_memory()
        yield eng
        eng.close()

    def test_log_and_query(self, engine):
        with engine.session() as sess:
            logger = AuditLogger(sess)
            logger.ensure_table()
            logger.log(AuditEntry(
                action=AuditAction.INSERT.value,
                table_name="trades",
                new_value={"symbol": "RELIANCE"},
                timestamp=time.time(),
            ))
            entries = logger.query(table_name="trades")
            assert len(entries) == 1
            assert entries[0].action == AuditAction.INSERT.value

    def test_purge_old(self, engine):
        with engine.session() as sess:
            logger = AuditLogger(sess)
            logger.ensure_table()
            # Log entry with very old timestamp
            old_entry = AuditEntry(
                action=AuditAction.DELETE.value,
                table_name="archive",
                timestamp=time.time() - 100 * 86400,
            )
            logger.log(old_entry)
            removed = logger.purge_old(retain_days=10)
            assert removed == 1

    def test_query_by_action(self, engine):
        with engine.session() as sess:
            logger = AuditLogger(sess)
            logger.ensure_table()
            for action in [AuditAction.INSERT, AuditAction.UPDATE, AuditAction.DELETE]:
                logger.log(AuditEntry(action=action.value, timestamp=time.time()))
            updates = logger.query(action=AuditAction.UPDATE.value)
            assert all(e.action == AuditAction.UPDATE.value for e in updates)


# ---------------------------------------------------------------------------
# 11. BackupManager
# ---------------------------------------------------------------------------

class TestBackupManager:
    @pytest.fixture()
    def db_file(self, tmp_path):
        """Create a populated SQLite file."""
        db = tmp_path / "test.db"
        import sqlite3 as sq3
        conn = sq3.connect(str(db))
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        conn.execute("INSERT INTO t VALUES (1, 'hello')")
        conn.commit()
        conn.close()
        return str(db)

    def test_backup_and_restore(self, db_file, tmp_path):
        backup_dir = str(tmp_path / "backups")
        cfg = BackupConfig(backup_dir=backup_dir, compress=False, retention_days=0)
        mgr = BackupManager(db_path=db_file, config=cfg)
        rec = mgr.backup()
        assert os.path.exists(rec.backup_path)
        assert rec.size_bytes > 0

        # Restore to a new path
        restored = str(tmp_path / "restored.db")
        mgr.restore(rec.backup_path, target_path=restored)

        import sqlite3 as sq3
        conn = sq3.connect(restored)
        row = conn.execute("SELECT v FROM t WHERE id=1").fetchone()
        conn.close()
        assert row[0] == "hello"

    def test_backup_compressed(self, db_file, tmp_path):
        backup_dir = str(tmp_path / "backups_gz")
        cfg = BackupConfig(backup_dir=backup_dir, compress=True, retention_days=0)
        mgr = BackupManager(db_path=db_file, config=cfg)
        rec = mgr.backup()
        assert rec.compressed
        assert rec.backup_path.endswith(".gz")

    def test_restore_compressed(self, db_file, tmp_path):
        backup_dir = str(tmp_path / "backups_gz2")
        cfg = BackupConfig(backup_dir=backup_dir, compress=True, retention_days=0)
        mgr = BackupManager(db_path=db_file, config=cfg)
        rec = mgr.backup()
        restored = str(tmp_path / "restored_gz.db")
        mgr.restore(rec.backup_path, target_path=restored)
        assert os.path.exists(restored)

    def test_verify(self, db_file, tmp_path):
        cfg = BackupConfig(backup_dir=str(tmp_path / "bk"), compress=False, retention_days=0)
        mgr = BackupManager(db_path=db_file, config=cfg)
        rec = mgr.backup()
        assert mgr.verify(rec.backup_path)


# ---------------------------------------------------------------------------
# 12. IndexManager
# ---------------------------------------------------------------------------

class TestIndexManager:
    @pytest.fixture()
    def engine(self):
        eng = make_in_memory()
        with eng.session() as sess:
            sess.execute(
                "CREATE TABLE trades (id INTEGER PRIMARY KEY, symbol TEXT, qty INTEGER)"
            )
        yield eng
        eng.close()

    def test_create_and_exists(self, engine):
        with engine.session() as sess:
            mgr = IndexManager(sess)
            defn = IndexDefinition(
                name="idx_trades_symbol",
                table="trades",
                columns=["symbol"],
            )
            mgr.create(defn)
            assert mgr.exists("idx_trades_symbol")

    def test_list_for_table(self, engine):
        with engine.session() as sess:
            mgr = IndexManager(sess)
            mgr.create(IndexDefinition("idx_t_sym", "trades", ["symbol"]))
            indexes = mgr.list_for_table("trades")
            names = [r["name"] for r in indexes]
            assert "idx_t_sym" in names

    def test_drop(self, engine):
        with engine.session() as sess:
            mgr = IndexManager(sess)
            mgr.create(IndexDefinition("idx_drop_me", "trades", ["qty"]))
            assert mgr.exists("idx_drop_me")
            mgr.drop("idx_drop_me")
            assert not mgr.exists("idx_drop_me")

    def test_create_unique_index(self, engine):
        with engine.session() as sess:
            mgr = IndexManager(sess)
            mgr.create(IndexDefinition(
                "idx_uni", "trades", ["symbol"], unique=True
            ))
            assert mgr.exists("idx_uni")


# ---------------------------------------------------------------------------
# 13. DatabaseFactory
# ---------------------------------------------------------------------------

class TestDatabaseFactory:
    def test_create_from_config(self):
        eng = DatabaseFactory.create(make_config())
        assert eng is not None
        eng.close()

    def test_sqlite(self, tmp_path):
        db = str(tmp_path / "f.db")
        eng = DatabaseFactory.sqlite(db, name="fac_sqlite")
        with eng.session() as sess:
            sess.execute("CREATE TABLE x (id INTEGER PRIMARY KEY)")
        eng.close()
        assert os.path.exists(db)

    def test_in_memory(self):
        eng = DatabaseFactory.in_memory()
        with eng.session() as sess:
            rows = sess.query("SELECT 1 AS v")
            assert rows[0]["v"] == 1
        eng.close()

    def test_invalid_pool_size_raises(self):
        cfg = make_config()
        cfg.pool.size = 0
        with pytest.raises(ConfigurationError):
            DatabaseFactory.create(cfg)


# ---------------------------------------------------------------------------
# 14. DatabaseRegistry
# ---------------------------------------------------------------------------

class TestDatabaseRegistry:
    def setup_method(self):
        reset_database_registry()

    def teardown_method(self):
        reset_database_registry()

    def test_register_and_get(self):
        reg = get_database_registry()
        eng = make_in_memory()
        reg.register("mydb", eng)
        assert reg.get("mydb") is eng
        reg.close_all()

    def test_default(self):
        reg = get_database_registry()
        eng = make_in_memory()
        reg.register("first", eng)
        assert reg.default() is eng
        reg.close_all()

    def test_not_found_raises(self):
        reg = get_database_registry()
        with pytest.raises(EngineNotFoundError):
            reg.get("doesnotexist")

    def test_duplicate_raises(self):
        reg = get_database_registry()
        eng = make_in_memory()
        reg.register("dup", eng)
        eng2 = make_in_memory()
        try:
            with pytest.raises(DatabaseError):
                reg.register("dup", eng2)
        finally:
            eng2.close()
        reg.close_all()

    def test_unregister(self):
        reg = get_database_registry()
        eng = make_in_memory()
        reg.register("temp", eng)
        removed = reg.unregister("temp", close=True)
        assert removed
        assert not reg.has("temp")

    def test_set_default(self):
        reg = get_database_registry()
        e1 = make_in_memory()
        e2 = make_in_memory()
        reg.register("a", e1)
        reg.register("b", e2)
        reg.set_default("b")
        assert reg.default() is e2
        reg.close_all()


# ---------------------------------------------------------------------------
# 15. DatabaseManager (integration)
# ---------------------------------------------------------------------------

class TestDatabaseManager:
    def setup_method(self):
        reset_database_manager()
        reset_database_registry()

    def teardown_method(self):
        reset_database_manager()
        reset_database_registry()

    def test_configure_and_session(self):
        mgr = get_database_manager()
        cfg = make_config()
        mgr.configure("main", cfg)
        with mgr.session("main") as sess:
            sess.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
            sess.execute("INSERT INTO t VALUES (42)")
        with mgr.session("main") as sess:
            row = sess.query_one("SELECT * FROM t")
            assert row["id"] == 42
        mgr.close_all()

    def test_query_helper(self):
        mgr = get_database_manager()
        eng = mgr.in_memory("q_helper")
        with mgr.session("q_helper") as sess:
            sess.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
            sess.execute("INSERT INTO t VALUES (1, 'hello')")
        rows = mgr.query("q_helper", "SELECT * FROM t")
        assert len(rows) == 1
        mgr.close_all()

    def test_execute_helper(self):
        mgr = get_database_manager()
        mgr.in_memory("exec_helper")
        with mgr.session("exec_helper") as sess:
            sess.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        count = mgr.execute("exec_helper", "INSERT INTO t VALUES (99)")
        assert count == 1
        mgr.close_all()

    def test_table_exists(self):
        mgr = get_database_manager()
        mgr.in_memory("te")
        with mgr.session("te") as sess:
            assert not mgr.table_exists("te", "foo")
            sess.execute("CREATE TABLE foo (id INTEGER PRIMARY KEY)")
        assert mgr.table_exists("te", "foo")
        mgr.close_all()

    def test_metrics(self):
        mgr = get_database_manager()
        mgr.in_memory("met")
        with mgr.session("met") as sess:
            sess.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
        report = mgr.metrics("met")
        assert "total_queries" in report
        mgr.close_all()

    def test_singleton(self):
        a = get_database_manager()
        b = get_database_manager()
        assert a is b

    def test_reset(self):
        a = get_database_manager()
        reset_database_manager()
        b = get_database_manager()
        assert a is not b


# ---------------------------------------------------------------------------
# 16. DatabaseContext
# ---------------------------------------------------------------------------

class TestDatabaseContext:
    def test_with_session_pushes_pops(self):
        eng = make_in_memory()
        assert current_session() is None
        with with_session(eng) as sess:
            assert current_session() is sess
        assert current_session() is None
        eng.close()

    def test_database_context(self):
        eng = make_in_memory()
        ctx = DatabaseContext(eng)
        with ctx.session() as sess:
            assert ctx.current is sess
        eng.close()


# ---------------------------------------------------------------------------
# 17. DatabaseMetrics
# ---------------------------------------------------------------------------

class TestDatabaseMetrics:
    def test_record_and_report(self):
        m = DatabaseMetrics()
        m.record("SELECT 1", 5.0, rows_affected=1)
        m.record("INSERT INTO t VALUES (?)", 2.0, rows_affected=1)
        report = m.report()
        assert report["total_queries"] == 2
        assert report["avg_duration_ms"] == 3.5

    def test_slow_queries(self):
        m = DatabaseMetrics()
        m.record("FAST", 10.0)
        m.record("SLOW", 200.0)
        slow = m.slow_queries(threshold_ms=100.0)
        assert len(slow) == 1
        assert slow[0].sql == "SLOW"

    def test_measure_context(self):
        m = DatabaseMetrics()
        with m.measure("SELECT count(*)") as ctx:
            ctx.rows = 5
        report = m.report()
        assert report["total_queries"] == 1

    def test_reset(self):
        m = DatabaseMetrics()
        m.record("Q", 1.0)
        m.reset()
        assert m.report()["total_queries"] == 0
