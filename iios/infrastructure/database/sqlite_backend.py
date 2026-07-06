"""
iios/infrastructure/database/sqlite_backend.py
===============================================
SQLite backend with connection pool simulation (single-file SQLite).
"""

from __future__ import annotations

import contextlib
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Generator, Optional

from ..infrastructure_exceptions import InfrastructureError

__all__ = ["SQLiteBackend"]


class SQLiteBackend:
    """Thread-safe SQLite backend using a per-thread connection.

    Usage::

        db = SQLiteBackend("data/iios.db")
        db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO jobs VALUES (?,?)", ("1", "morning"))
        rows = db.query("SELECT * FROM jobs")
    """

    def __init__(self, path: str = "data/iios.db", check_same_thread: bool = False) -> None:
        self._path = path
        self._check_same_thread = check_same_thread
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_lock = threading.Lock()
        self._initialized = False

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "connection", None)
        if conn is None:
            conn = sqlite3.connect(
                self._path,
                check_same_thread=self._check_same_thread,
                isolation_level=None,  # autocommit; we control transactions
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.connection = conn
        return conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._get_conn()
        conn.execute("BEGIN")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        try:
            return self._get_conn().execute(sql, params)
        except sqlite3.Error as exc:
            raise InfrastructureError(
                f"SQLite execute failed: {exc}", code="INF-DB-001"
            ) from exc

    def executemany(self, sql: str, params_seq: Any) -> sqlite3.Cursor:
        try:
            return self._get_conn().executemany(sql, params_seq)
        except sqlite3.Error as exc:
            raise InfrastructureError(
                f"SQLite executemany failed: {exc}", code="INF-DB-002"
            ) from exc

    def query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        cursor = self.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def query_one(self, sql: str, params: tuple = ()) -> Optional[dict[str, Any]]:
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def close(self) -> None:
        conn = getattr(self._local, "connection", None)
        if conn is not None:
            conn.close()
            self._local.connection = None

    @property
    def path(self) -> str:
        return self._path
