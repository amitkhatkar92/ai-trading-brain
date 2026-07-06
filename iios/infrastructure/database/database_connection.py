"""
iios/infrastructure/database/database_connection.py
====================================================
Connection abstraction with SQLite, PostgreSQL, MySQL, and DuckDB backends.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Iterator, Optional, Sequence

from .database_config import DatabaseConfig
from .database_constants import DatabaseEngine, ConnectionState
from .database_exceptions import (
    ConnectionError,
    QueryError,
    IntegrityError,
    DuplicateKeyError,
    UnsupportedEngineError,
)

__all__ = [
    "DatabaseConnection",
    "SQLiteConnection",
    "PostgreSQLConnection",
    "MySQLConnection",
    "DuckDBConnection",
    "Row",
]

Row = dict[str, Any]


class DatabaseConnection(ABC):
    """Abstract base class for all database connections."""

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._connection_id = str(uuid.uuid4())
        self._state = ConnectionState.IDLE
        self._created_at = time.monotonic()
        self._last_used = time.monotonic()
        self._query_count = 0
        self._in_transaction = False

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def open(self) -> None:
        """Open the underlying driver connection."""

    @abstractmethod
    def close(self) -> None:
        """Close and release the underlying connection."""

    @abstractmethod
    def execute(self, sql: str, params: Sequence[Any] = ()) -> "Cursor":
        """Execute a SQL statement; return a cursor-like object."""

    @abstractmethod
    def executemany(self, sql: str, params_seq: Sequence[Sequence[Any]]) -> None:
        """Execute a statement against a sequence of parameter tuples."""

    @abstractmethod
    def begin(self) -> None:
        """Begin a transaction explicitly."""

    @abstractmethod
    def commit(self) -> None:
        """Commit the current transaction."""

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the current transaction."""

    @abstractmethod
    def savepoint(self, name: str) -> None:
        """Create a named savepoint."""

    @abstractmethod
    def rollback_to(self, name: str) -> None:
        """Rollback to a named savepoint."""

    @abstractmethod
    def release_savepoint(self, name: str) -> None:
        """Release a named savepoint."""

    # ── Shared helpers ────────────────────────────────────────────────────────

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[Row]:
        """Execute a SELECT and return all rows as dicts."""
        cursor = self.execute(sql, params)
        return cursor.fetchall()

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[Row]:
        """Execute a SELECT and return the first row or None."""
        cursor = self.execute(sql, params)
        return cursor.fetchone()

    @property
    def connection_id(self) -> str:
        return self._connection_id

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def in_transaction(self) -> bool:
        return self._in_transaction

    @property
    def age(self) -> float:
        """Seconds since connection was created."""
        return time.monotonic() - self._created_at

    @property
    def idle_time(self) -> float:
        """Seconds since connection was last used."""
        return time.monotonic() - self._last_used

    @property
    def query_count(self) -> int:
        return self._query_count

    def _touch(self) -> None:
        self._last_used = time.monotonic()
        self._query_count += 1


class Cursor:
    """Unified cursor interface that returns Row dicts."""

    def __init__(self, raw_cursor: Any, description: Optional[list] = None) -> None:
        self._cursor = raw_cursor
        self._description = description or (getattr(raw_cursor, "description", None))

    def _col_names(self) -> list[str]:
        if self._description:
            return [col[0] for col in self._description]
        desc = getattr(self._cursor, "description", None)
        return [col[0] for col in desc] if desc else []

    def fetchone(self) -> Optional[Row]:
        row = self._cursor.fetchone()
        if row is None:
            return None
        cols = self._col_names()
        if cols and not isinstance(row, dict):
            return dict(zip(cols, row))
        return dict(row) if hasattr(row, "keys") else row

    def fetchall(self) -> list[Row]:
        rows = self._cursor.fetchall()
        cols = self._col_names()
        if not rows:
            return []
        if cols and not isinstance(rows[0], dict):
            return [dict(zip(cols, r)) for r in rows]
        return [dict(r) if hasattr(r, "keys") else r for r in rows]

    def fetchmany(self, size: int = 100) -> list[Row]:
        rows = self._cursor.fetchmany(size)
        cols = self._col_names()
        if not rows:
            return []
        if cols and not isinstance(rows[0], dict):
            return [dict(zip(cols, r)) for r in rows]
        return [dict(r) if hasattr(r, "keys") else r for r in rows]

    @property
    def lastrowid(self) -> Optional[int]:
        return getattr(self._cursor, "lastrowid", None)

    @property
    def rowcount(self) -> int:
        return getattr(self._cursor, "rowcount", -1)

    def __iter__(self) -> Iterator[Row]:
        cols = self._col_names()
        for row in self._cursor:
            if cols and not isinstance(row, dict):
                yield dict(zip(cols, row))
            else:
                yield dict(row) if hasattr(row, "keys") else row


# ── SQLite connection ─────────────────────────────────────────────────────────

def _map_sqlite_error(exc: sqlite3.Error, sql: str = "") -> QueryError:
    msg = str(exc)
    if "UNIQUE constraint failed" in msg:
        return DuplicateKeyError()
    if "FOREIGN KEY constraint failed" in msg:
        from .database_exceptions import ForeignKeyError
        return ForeignKeyError()
    if "NOT NULL constraint failed" in msg:
        from .database_exceptions import NotNullError
        return NotNullError()
    if "IntegrityError" in type(exc).__name__ or "constraint" in msg.lower():
        return IntegrityError(msg, sql=sql)
    return QueryError(msg, sql=sql)


class SQLiteConnection(DatabaseConnection):
    """SQLite3 connection using WAL mode and thread-local access."""

    def __init__(self, config: DatabaseConfig) -> None:
        super().__init__(config)
        self._conn: Optional[sqlite3.Connection] = None

    def open(self) -> None:
        try:
            self._conn = sqlite3.connect(
                self._config.url,
                check_same_thread=self._config.check_same_thread,
                timeout=self._config.timeout,
                isolation_level=None,  # manual transaction control
            )
            self._conn.row_factory = sqlite3.Row
            if self._config.wal_mode:
                self._conn.execute("PRAGMA journal_mode=WAL")
            if self._config.foreign_keys:
                self._conn.execute("PRAGMA foreign_keys=ON")
            if self._config.busy_timeout:
                self._conn.execute(f"PRAGMA busy_timeout={self._config.busy_timeout}")
            self._state = ConnectionState.IDLE
        except sqlite3.Error as exc:
            self._state = ConnectionState.ERROR
            raise ConnectionError(f"Cannot open SQLite database '{self._config.url}': {exc}") from exc

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass
            finally:
                self._conn = None
                self._state = ConnectionState.CLOSED

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Cursor:
        if self._conn is None:
            raise ConnectionError("Connection is not open")
        try:
            self._touch()
            raw = self._conn.execute(sql, params)
            return Cursor(raw)
        except sqlite3.Error as exc:
            raise _map_sqlite_error(exc, sql) from exc

    def executemany(self, sql: str, params_seq: Sequence[Sequence[Any]]) -> None:
        if self._conn is None:
            raise ConnectionError("Connection is not open")
        try:
            self._touch()
            self._conn.executemany(sql, params_seq)
        except sqlite3.Error as exc:
            raise _map_sqlite_error(exc, sql) from exc

    def begin(self) -> None:
        isolation = self._config.isolation.value
        # SQLite uses DEFERRED/IMMEDIATE/EXCLUSIVE for BEGIN
        mode = isolation if isolation in ("DEFERRED", "IMMEDIATE", "EXCLUSIVE") else "DEFERRED"
        self.execute(f"BEGIN {mode}")
        self._in_transaction = True

    def commit(self) -> None:
        self.execute("COMMIT")
        self._in_transaction = False

    def rollback(self) -> None:
        self.execute("ROLLBACK")
        self._in_transaction = False

    def savepoint(self, name: str) -> None:
        self.execute(f"SAVEPOINT {name}")

    def rollback_to(self, name: str) -> None:
        self.execute(f"ROLLBACK TO SAVEPOINT {name}")

    def release_savepoint(self, name: str) -> None:
        self.execute(f"RELEASE SAVEPOINT {name}")

    @property
    def raw(self) -> Optional[sqlite3.Connection]:
        return self._conn


# ── Stub backends for non-SQLite drivers ─────────────────────────────────────

class _StubConnection(DatabaseConnection):
    """Base stub for drivers that need an optional install."""

    _DRIVER_NAME: str = "unknown"
    _INSTALL_CMD: str = "pip install <driver>"

    def __init__(self, config: DatabaseConfig) -> None:
        super().__init__(config)
        self._raise()

    def _raise(self) -> None:
        raise UnsupportedEngineError(
            f"{self._DRIVER_NAME} driver not installed. Run: {self._INSTALL_CMD}"
        )

    def open(self) -> None: self._raise()
    def close(self) -> None: pass
    def execute(self, sql: str, params: Sequence[Any] = ()) -> Cursor: self._raise()  # type: ignore
    def executemany(self, sql: str, params_seq: Sequence[Sequence[Any]]) -> None: self._raise()
    def begin(self) -> None: self._raise()
    def commit(self) -> None: self._raise()
    def rollback(self) -> None: self._raise()
    def savepoint(self, name: str) -> None: self._raise()
    def rollback_to(self, name: str) -> None: self._raise()
    def release_savepoint(self, name: str) -> None: self._raise()


class PostgreSQLConnection(_StubConnection):
    """PostgreSQL connection (requires psycopg2 or psycopg3)."""
    _DRIVER_NAME = "psycopg2/psycopg3"
    _INSTALL_CMD = "pip install psycopg2-binary"

    def __init__(self, config: DatabaseConfig) -> None:
        # Try actual import first
        try:
            import psycopg2  # noqa: F401
            # Full implementation would go here
            DatabaseConnection.__init__(self, config)
        except ImportError:
            super().__init__(config)


class MySQLConnection(_StubConnection):
    """MySQL connection (requires pymysql)."""
    _DRIVER_NAME = "pymysql"
    _INSTALL_CMD = "pip install pymysql"


class DuckDBConnection(_StubConnection):
    """DuckDB connection (requires duckdb)."""
    _DRIVER_NAME = "duckdb"
    _INSTALL_CMD = "pip install duckdb"

    def __init__(self, config: DatabaseConfig) -> None:
        try:
            import duckdb  # noqa: F401
            DatabaseConnection.__init__(self, config)
            self._duckdb_conn: Any = None
        except ImportError:
            _StubConnection.__init__(self, config)

    def open(self) -> None:
        try:
            import duckdb
            self._duckdb_conn = duckdb.connect(self._config.url)
            self._state = ConnectionState.IDLE
        except ImportError:
            raise UnsupportedEngineError("duckdb not installed. Run: pip install duckdb")

    def close(self) -> None:
        if self._duckdb_conn:
            self._duckdb_conn.close()
            self._duckdb_conn = None
            self._state = ConnectionState.CLOSED

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Cursor:
        self._touch()
        raw = self._duckdb_conn.execute(sql, list(params))
        return Cursor(raw, description=raw.description if hasattr(raw, "description") else None)

    def executemany(self, sql: str, params_seq: Sequence[Sequence[Any]]) -> None:
        for params in params_seq:
            self.execute(sql, params)

    def begin(self) -> None:
        self.execute("BEGIN")
        self._in_transaction = True

    def commit(self) -> None:
        self.execute("COMMIT")
        self._in_transaction = False

    def rollback(self) -> None:
        self.execute("ROLLBACK")
        self._in_transaction = False

    def savepoint(self, name: str) -> None:
        self.execute(f"SAVEPOINT {name}")

    def rollback_to(self, name: str) -> None:
        self.execute(f"ROLLBACK TO SAVEPOINT {name}")

    def release_savepoint(self, name: str) -> None:
        self.execute(f"RELEASE SAVEPOINT {name}")


def create_connection(config: DatabaseConfig) -> DatabaseConnection:
    """Factory: create a ``DatabaseConnection`` for the given config."""
    engine = config.engine
    if engine == DatabaseEngine.SQLITE:
        conn = SQLiteConnection(config)
        conn.open()
        return conn
    if engine == DatabaseEngine.POSTGRESQL:
        conn = PostgreSQLConnection(config)
        conn.open()
        return conn
    if engine == DatabaseEngine.MYSQL:
        conn = MySQLConnection(config)
        conn.open()
        return conn
    if engine == DatabaseEngine.DUCKDB:
        conn = DuckDBConnection(config)
        conn.open()
        return conn
    raise UnsupportedEngineError(str(engine))
