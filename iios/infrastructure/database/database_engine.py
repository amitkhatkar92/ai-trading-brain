"""
iios/infrastructure/database/database_engine.py
================================================
DatabaseEngine: manages a connection pool, sessions, metrics and cache.
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional

from .database_config import DatabaseConfig
from .database_connection import DatabaseConnection, create_connection
from .database_session import DatabaseSession
from .database_constants import DatabaseEngine as EngineType
from .database_exceptions import ConnectionError, SessionError
from .performance.connection_pool import ConnectionPool
from .performance.query_cache import QueryCache
from .performance.metrics import DatabaseMetrics

__all__ = ["DatabaseEngine"]

_LOG = logging.getLogger("iios.database.engine")


class DatabaseEngine:
    """Central database engine providing sessions, pooling, cache and metrics.

    Usage::

        engine = DatabaseEngine(config)

        with engine.session() as sess:
            rows = sess.query("SELECT * FROM trades")
            sess.execute("INSERT INTO trades VALUES (?,?,?)", (...))

        engine.close()
    """

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._name = config.name
        self._lock = threading.RLock()
        self._closed = False

        # For SQLite :memory: databases, skip pooling and use a single shared connection
        self._shared_mode = (
            config.engine == EngineType.SQLITE and config.url == ":memory:"
        )

        if self._shared_mode:
            # Single connection for in-memory SQLite (per-thread would lose data)
            self._shared_conn: Optional[DatabaseConnection] = create_connection(config)
            self._pool: Optional[ConnectionPool] = None
        else:
            self._shared_conn = None
            self._pool = ConnectionPool(config)

        self._cache = QueryCache(
            max_size=config.cache.max_size,
            default_ttl=config.cache.ttl,
            exclude_tables=config.cache.exclude_tables,
        ) if config.cache.enabled else None

        self._metrics = DatabaseMetrics()
        self._session_count = 0

    # ── Session factory ───────────────────────────────────────────────────────

    @contextmanager
    def session(self) -> Generator[DatabaseSession, None, None]:
        """Context-manager that yields an auto-transacting DatabaseSession.

        Commits on clean exit, rolls back on exception.
        """
        conn = self._acquire()
        sess = DatabaseSession(
            connection=conn,
            echo=self._config.echo,
            audit_fn=self._make_audit_fn(),
        )
        self._session_count += 1
        self._metrics.record_session()
        try:
            with sess:
                yield sess
        finally:
            self._release(conn)

    def raw_connection(self) -> DatabaseConnection:
        """Acquire a raw connection (caller is responsible for release)."""
        return self._acquire()

    def release_connection(self, conn: DatabaseConnection) -> None:
        """Return a raw connection to the pool."""
        self._release(conn)

    # ── One-shot helpers ──────────────────────────────────────────────────────

    def execute(self, sql: str, params: tuple = ()) -> Any:
        """Execute a DML statement and return rowcount."""
        with self.session() as sess:
            result = sess.execute(sql, params)
            return result.rowcount

    def query(self, sql: str, params: tuple = (), cache: bool = True) -> list[dict]:
        """Execute a SELECT and return all rows."""
        if cache and self._cache:
            cached = self._cache.get(sql, params)
            if cached is not None:
                return cached

        with self.session() as sess:
            rows = sess.query(sql, params)

        if cache and self._cache:
            self._cache.set(sql, params, rows)

        return rows

    def query_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        with self.session() as sess:
            return sess.query_one(sql, params)

    def table_exists(self, table_name: str) -> bool:
        with self.session() as sess:
            return sess.table_exists(table_name)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def close(self) -> None:
        """Close all connections and clean up resources."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
        if self._pool:
            self._pool.close_all()
        if self._shared_conn:
            self._shared_conn.close()
            self._shared_conn = None
        _LOG.info("DatabaseEngine '%s' closed", self._name)

    def __enter__(self) -> "DatabaseEngine":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def config(self) -> DatabaseConfig:
        return self._config

    @property
    def metrics(self) -> DatabaseMetrics:
        return self._metrics

    @property
    def cache(self) -> Optional[QueryCache]:
        return self._cache

    @property
    def pool(self) -> Optional[ConnectionPool]:
        return self._pool

    @property
    def session_count(self) -> int:
        return self._session_count

    # ── Internal ──────────────────────────────────────────────────────────────

    def _acquire(self) -> DatabaseConnection:
        if self._closed:
            raise ConnectionError(f"Engine '{self._name}' is closed")
        if self._shared_mode and self._shared_conn:
            return self._shared_conn
        if self._pool:
            return self._pool.checkout()
        raise ConnectionError("No connection source available")

    def _release(self, conn: DatabaseConnection) -> None:
        if self._shared_mode:
            return  # shared conn is never released
        if self._pool:
            self._pool.checkin(conn)

    def _make_audit_fn(self) -> Optional[Callable]:
        """Return an audit callback (wired to audit logger later)."""
        return None  # wired by DatabaseManager if audit is enabled
