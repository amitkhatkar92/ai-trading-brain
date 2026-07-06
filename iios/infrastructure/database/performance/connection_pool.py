"""
iios/infrastructure/database/performance/connection_pool.py
===========================================================
Thread-safe connection pool for the IIOS Database Framework.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from ..database_config import DatabaseConfig
from ..database_connection import DatabaseConnection, ConnectionState, create_connection
from ..database_exceptions import ConnectionPoolExhausted, ConnectionTimeoutError

__all__ = ["ConnectionPool", "PoolStats"]


@dataclass
class PoolStats:
    """Runtime statistics for a connection pool."""
    total_created: int = 0
    total_destroyed: int = 0
    total_checkouts: int = 0
    total_checkins: int = 0
    total_timeouts: int = 0
    total_recycles: int = 0
    peak_active: int = 0
    current_active: int = 0
    current_idle: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.total_checkouts
        if total == 0:
            return 1.0
        timeouts = self.total_timeouts
        return 1.0 - (timeouts / total)


class ConnectionPool:
    """Thread-safe pool that manages a fixed number of DatabaseConnections.

    On checkout, if a connection exceeds *recycle* age it is closed and replaced.
    If the pool is exhausted and *overflow* connections are also in use, the
    caller waits up to *timeout* seconds before raising ``ConnectionPoolExhausted``.

    Usage::

        pool = ConnectionPool(config)
        conn = pool.checkout()
        try:
            conn.execute("SELECT 1")
        finally:
            pool.checkin(conn)

        # Or use as context manager:
        with pool.acquire() as conn:
            conn.execute("SELECT 1")
    """

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._pool_size = config.pool.size
        self._max_overflow = config.pool.max_overflow
        self._timeout = config.pool.timeout
        self._recycle = config.pool.recycle

        self._idle: queue.Queue[DatabaseConnection] = queue.Queue()
        self._active: set[str] = set()  # connection_ids of checked-out conns
        self._active_conns: dict[str, DatabaseConnection] = {}  # id → conn (for close_all)
        self._overflow_count = 0
        self._lock = threading.Lock()
        self._stats = PoolStats()
        self._closed = False

        # Pre-create connections up to pool_size
        self._initialize()

    def _initialize(self) -> None:
        for _ in range(self._pool_size):
            conn = self._new_connection()
            self._idle.put(conn)

    def _new_connection(self) -> DatabaseConnection:
        conn = create_connection(self._config)
        self._stats.total_created += 1
        self._stats.current_idle = self._idle.qsize()
        return conn

    def _destroy(self, conn: DatabaseConnection) -> None:
        try:
            conn.close()
        except Exception:
            pass
        self._stats.total_destroyed += 1

    def checkout(self, timeout: Optional[float] = None) -> DatabaseConnection:
        """Acquire a connection from the pool.

        Raises:
            ConnectionPoolExhausted: If no connection is available within *timeout*.
        """
        if self._closed:
            raise ConnectionPoolExhausted(self._pool_size, 0)

        deadline = time.monotonic() + (timeout or self._timeout)

        while True:
            # Try to get an idle connection
            try:
                conn = self._idle.get_nowait()
                conn = self._prepare(conn)
                with self._lock:
                    self._active.add(conn.connection_id)
                    self._active_conns[conn.connection_id] = conn
                    self._stats.total_checkouts += 1
                    active = len(self._active)
                    if active > self._stats.peak_active:
                        self._stats.peak_active = active
                    self._stats.current_active = active
                    self._stats.current_idle = self._idle.qsize()
                conn._state = ConnectionState.IN_USE
                return conn
            except queue.Empty:
                pass

            # No idle connections — try overflow
            with self._lock:
                if self._overflow_count < self._max_overflow:
                    self._overflow_count += 1
                    conn = self._new_connection()
                    self._active.add(conn.connection_id)
                    self._active_conns[conn.connection_id] = conn
                    self._stats.total_checkouts += 1
                    conn._state = ConnectionState.IN_USE
                    return conn

            # Wait a bit and retry
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._stats.total_timeouts += 1
                raise ConnectionPoolExhausted(
                    pool_size=self._pool_size,
                    timeout=timeout or self._timeout,
                )
            time.sleep(min(0.05, remaining))

    def checkin(self, conn: DatabaseConnection) -> None:
        """Return a connection to the pool."""
        with self._lock:
            self._active.discard(conn.connection_id)
            self._active_conns.pop(conn.connection_id, None)
            self._stats.total_checkins += 1
            self._stats.current_active = len(self._active)

        # If connection is too old, destroy it and create a fresh one
        if conn.age > self._recycle:
            self._destroy(conn)
            self._stats.total_recycles += 1
            if self._overflow_count > 0:
                with self._lock:
                    self._overflow_count -= 1
                return  # don't replace overflow connections
            try:
                conn = self._new_connection()
            except Exception:
                return
        else:
            # Rollback any pending transaction
            try:
                if conn.in_transaction:
                    conn.rollback()
            except Exception:
                self._destroy(conn)
                return

        conn._state = ConnectionState.IDLE
        # Return to overflow tracking if this is an overflow connection
        try:
            if self._idle.qsize() >= self._pool_size:
                # Overflow connection — just destroy it
                with self._lock:
                    if self._overflow_count > 0:
                        self._overflow_count -= 1
                self._destroy(conn)
            else:
                self._idle.put_nowait(conn)
                self._stats.current_idle = self._idle.qsize()
        except queue.Full:
            self._destroy(conn)

    def acquire(self, timeout: Optional[float] = None):
        """Context manager: checkout → yield → checkin."""
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            conn = self.checkout(timeout=timeout)
            try:
                yield conn
            finally:
                self.checkin(conn)

        return _ctx()

    def _prepare(self, conn: DatabaseConnection) -> DatabaseConnection:
        """Health-check a connection before returning it."""
        if not self._config.pool.pre_ping:
            return conn
        try:
            conn.execute("SELECT 1")
        except Exception:
            # Replace dead connection
            self._destroy(conn)
            self._stats.total_recycles += 1
            conn = self._new_connection()
        return conn

    def close_all(self) -> None:
        """Close all idle and in-use connections."""
        self._closed = True
        while not self._idle.empty():
            try:
                conn = self._idle.get_nowait()
                self._destroy(conn)
            except queue.Empty:
                break
        # Also close any still-active (checked-out) connections
        with self._lock:
            active_conns = list(self._active_conns.values())
            self._active_conns.clear()
            self._active.clear()
        for conn in active_conns:
            self._destroy(conn)

    @property
    def stats(self) -> PoolStats:
        self._stats.current_idle = self._idle.qsize()
        self._stats.current_active = len(self._active)
        return self._stats

    @property
    def pool_size(self) -> int:
        return self._pool_size

    @property
    def is_closed(self) -> bool:
        return self._closed
