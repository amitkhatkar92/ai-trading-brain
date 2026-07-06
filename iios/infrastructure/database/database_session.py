"""
iios/infrastructure/database/database_session.py
=================================================
Session with full transaction management, savepoints, and metrics.
"""

from __future__ import annotations

import time
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generator, Optional, Sequence

from .database_connection import DatabaseConnection, Row
from .database_exceptions import (
    SessionError,
    TransactionError,
    SavepointError,
    QueryError,
)
from .database_constants import MAX_SAVEPOINTS, QueryOperation, AuditAction

__all__ = ["DatabaseSession", "SessionStats"]


@dataclass
class SessionStats:
    """Per-session execution statistics."""
    queries_executed: int = 0
    rows_read: int = 0
    rows_written: int = 0
    transactions_committed: int = 0
    transactions_rolled_back: int = 0
    savepoints_created: int = 0
    total_duration_ms: float = 0.0
    errors: int = 0

    def record(self, rows: int = 0, written: bool = False, duration_ms: float = 0.0) -> None:
        self.queries_executed += 1
        self.total_duration_ms += duration_ms
        if written:
            self.rows_written += rows
        else:
            self.rows_read += rows


class DatabaseSession:
    """Wraps a connection and provides transaction-managed query execution.

    Usage::

        with engine.session() as sess:
            rows = sess.query("SELECT * FROM trades WHERE symbol=?", ("RELIANCE",))
            sess.execute("INSERT INTO trades (symbol, qty) VALUES (?,?)", ("RELIANCE", 10))
            # auto-commit on __exit__, rollback on exception

        # savepoints
        with engine.session() as sess:
            with sess.savepoint("sp1"):
                sess.execute(...)   # rolled back on error, but outer txn survives
    """

    def __init__(
        self,
        connection: DatabaseConnection,
        echo: bool = False,
        audit_fn: Optional[Any] = None,   # callable(action, sql, duration_ms)
    ) -> None:
        self._conn = connection
        self._echo = echo
        self._audit_fn = audit_fn
        self._session_id = str(uuid.uuid4())
        self._stats = SessionStats()
        self._savepoint_stack: list[str] = []
        self._active = True
        self._lock = threading.RLock()

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "DatabaseSession":
        self.begin()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False  # don't suppress exceptions

    # ── Transaction management ────────────────────────────────────────────────

    def begin(self) -> None:
        with self._lock:
            if not self._active:
                raise SessionError("Session is closed", code="DB-SES-002")
            if not self._conn.in_transaction:
                self._conn.begin()

    def commit(self) -> None:
        with self._lock:
            if not self._active:
                return
            try:
                if self._conn.in_transaction:
                    self._conn.commit()
                    self._stats.transactions_committed += 1
            except Exception as exc:
                raise TransactionError(f"Commit failed: {exc}") from exc

    def rollback(self) -> None:
        with self._lock:
            if not self._active:
                return
            try:
                self._savepoint_stack.clear()
                if self._conn.in_transaction:
                    self._conn.rollback()
                    self._stats.transactions_rolled_back += 1
            except Exception as exc:
                raise TransactionError(f"Rollback failed: {exc}") from exc

    @contextmanager
    def savepoint(self, name: Optional[str] = None) -> Generator[str, None, None]:
        """Create and manage a named savepoint."""
        if len(self._savepoint_stack) >= MAX_SAVEPOINTS:
            raise SavepointError(f"Max savepoints ({MAX_SAVEPOINTS}) exceeded")
        sp_name = name or f"sp_{len(self._savepoint_stack)}_{uuid.uuid4().hex[:8]}"
        self._conn.savepoint(sp_name)
        self._savepoint_stack.append(sp_name)
        self._stats.savepoints_created += 1
        try:
            yield sp_name
            self._conn.release_savepoint(sp_name)
        except Exception:
            self._conn.rollback_to(sp_name)
            self._conn.release_savepoint(sp_name)
            raise
        finally:
            if sp_name in self._savepoint_stack:
                self._savepoint_stack.remove(sp_name)

    # ── Query execution ───────────────────────────────────────────────────────

    def execute(self, sql: str, params: Sequence[Any] = ()) -> "ExecuteResult":
        """Execute a DML/DDL statement. Returns an ExecuteResult."""
        t0 = time.monotonic()
        try:
            cursor = self._conn.execute(sql, params)
            duration_ms = (time.monotonic() - t0) * 1000
            self._stats.record(rows=cursor.rowcount, written=True, duration_ms=duration_ms)
            if self._echo:
                _log_sql(sql, params, duration_ms)
            self._audit(AuditAction.INSERT, sql, duration_ms)
            return ExecuteResult(
                lastrowid=cursor.lastrowid,
                rowcount=cursor.rowcount,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            self._stats.errors += 1
            raise

    def executemany(self, sql: str, params_seq: Sequence[Sequence[Any]]) -> None:
        """Execute a statement against a sequence of parameter tuples."""
        t0 = time.monotonic()
        try:
            self._conn.executemany(sql, params_seq)
            duration_ms = (time.monotonic() - t0) * 1000
            self._stats.record(rows=len(list(params_seq)), written=True, duration_ms=duration_ms)
        except Exception as exc:
            self._stats.errors += 1
            raise

    def query(self, sql: str, params: Sequence[Any] = ()) -> list[Row]:
        """Execute a SELECT and return all rows as dicts."""
        t0 = time.monotonic()
        try:
            rows = self._conn.query(sql, params)
            duration_ms = (time.monotonic() - t0) * 1000
            self._stats.record(rows=len(rows), written=False, duration_ms=duration_ms)
            if self._echo:
                _log_sql(sql, params, duration_ms)
            return rows
        except Exception as exc:
            self._stats.errors += 1
            raise

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[Row]:
        """Execute a SELECT and return the first row or None."""
        t0 = time.monotonic()
        try:
            row = self._conn.query_one(sql, params)
            duration_ms = (time.monotonic() - t0) * 1000
            self._stats.record(rows=1 if row else 0, written=False, duration_ms=duration_ms)
            return row
        except Exception as exc:
            self._stats.errors += 1
            raise

    def query_scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        """Execute a SELECT and return the first column of the first row."""
        row = self._conn.query_one(sql, params)
        if row is None:
            return None
        return next(iter(row.values()), None)

    def query_paginated(
        self,
        sql: str,
        params: Sequence[Any] = (),
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Row], int]:
        """Execute a paginated SELECT.

        Returns:
            (rows, total_count) tuple.
        """
        offset = (page - 1) * page_size
        # Count total
        count_sql = f"SELECT COUNT(*) AS cnt FROM ({sql}) AS _subq"
        total_row = self.query_one(count_sql, params)
        total = int(total_row["cnt"]) if total_row else 0
        # Fetch page
        page_sql = f"{sql} LIMIT ? OFFSET ?"
        rows = self.query(page_sql, (*params, page_size, offset))
        return rows, total

    def table_exists(self, table_name: str) -> bool:
        """Check whether a table exists in the current database."""
        row = self.query_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        return row is not None

    def close(self) -> None:
        """Close the underlying connection."""
        with self._lock:
            self._active = False
            self._conn.close()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def stats(self) -> SessionStats:
        return self._stats

    @property
    def in_transaction(self) -> bool:
        return self._conn.in_transaction

    @property
    def connection(self) -> DatabaseConnection:
        return self._conn

    # ── Internal ──────────────────────────────────────────────────────────────

    def _audit(self, action: AuditAction, sql: str, duration_ms: float) -> None:
        if self._audit_fn:
            try:
                self._audit_fn(action=action, sql=sql, duration_ms=duration_ms)
            except Exception:
                pass


@dataclass
class ExecuteResult:
    """Result of a non-SELECT SQL statement."""
    lastrowid: Optional[int] = None
    rowcount: int = 0
    duration_ms: float = 0.0


def _log_sql(sql: str, params: Sequence[Any], duration_ms: float) -> None:
    import logging
    _LOG = logging.getLogger("iios.database.sql")
    _LOG.debug("%.2fms  %s  %s", duration_ms, sql[:200], params)
