"""iios/execution/brokers/connection/connection_pool.py"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from iios.execution.brokers.broker_constants import (
    DEFAULT_CONNECT_TIMEOUT_SEC,
    DEFAULT_MAX_CONNECTIONS,
    ConnectionStatus,
)
from iios.execution.brokers.broker_exceptions import BrokerRegistryOverflowError
from iios.execution.brokers.core.broker_connection import BrokerConnection

logger = logging.getLogger(__name__)


@dataclass
class PoolEntry:
    """One slot in the connection pool."""

    connection: BrokerConnection
    added_at:   float = field(default_factory=time.time)
    last_used:  float = field(default_factory=time.time)

    def touch(self) -> None:
        self.last_used = time.time()

    def idle_sec(self) -> float:
        return time.time() - self.last_used


class ConnectionPool:
    """
    Broker-independent connection pool.

    Maintains at most *max_connections* BrokerConnection objects, keyed by
    broker_id.  Provides acquire / release semantics without real TCP pooling
    (broker network logic lives in the adapter); this class tracks logical
    connection state only.
    """

    def __init__(
        self,
        max_connections:     int   = DEFAULT_MAX_CONNECTIONS,
        connect_timeout_sec: float = DEFAULT_CONNECT_TIMEOUT_SEC,
        idle_timeout_sec:    float = 300.0,
    ) -> None:
        self._max_connections     = max_connections
        self._connect_timeout_sec = connect_timeout_sec
        self._idle_timeout_sec    = idle_timeout_sec
        self._pool: dict[str, PoolEntry] = {}
        self._lock = threading.RLock()

    # ── Pool operations ───────────────────────────────────────────────────────

    def acquire(self, broker_id: str) -> BrokerConnection:
        """Return the BrokerConnection for *broker_id*, creating one if needed."""
        with self._lock:
            entry = self._pool.get(broker_id)
            if entry is not None:
                entry.touch()
                return entry.connection
            # Create a new slot
            if len(self._pool) >= self._max_connections:
                # evict oldest idle first
                evicted = self._evict_one()
                if evicted is None:
                    raise BrokerRegistryOverflowError(
                        f"Connection pool full ({self._max_connections}); "
                        "cannot acquire for broker %s" % broker_id,
                        "BAF-081",
                    )
            conn  = BrokerConnection(broker_id=broker_id)
            entry = PoolEntry(connection=conn)
            self._pool[broker_id] = entry
            logger.debug("ConnectionPool: allocated slot for broker %s", broker_id)
            return conn

    def release(self, broker_id: str) -> None:
        """Mark connection as released (does not remove from pool)."""
        with self._lock:
            entry = self._pool.get(broker_id)
            if entry:
                entry.touch()

    def remove(self, broker_id: str) -> None:
        """Remove connection from pool (called on disconnect)."""
        with self._lock:
            self._pool.pop(broker_id, None)
            logger.debug("ConnectionPool: removed broker %s", broker_id)

    def get(self, broker_id: str) -> BrokerConnection | None:
        with self._lock:
            entry = self._pool.get(broker_id)
            return entry.connection if entry else None

    def has(self, broker_id: str) -> bool:
        with self._lock:
            return broker_id in self._pool

    def connected_broker_ids(self) -> list[str]:
        with self._lock:
            return [
                bid
                for bid, entry in self._pool.items()
                if entry.connection.status == ConnectionStatus.CONNECTED
            ]

    def all_broker_ids(self) -> list[str]:
        with self._lock:
            return list(self._pool.keys())

    def size(self) -> int:
        with self._lock:
            return len(self._pool)

    def purge_idle(self) -> int:
        """Remove connections idle longer than *idle_timeout_sec*."""
        with self._lock:
            idle = [
                bid
                for bid, entry in self._pool.items()
                if entry.idle_sec() > self._idle_timeout_sec
                   and not entry.connection.is_connected()
            ]
            for bid in idle:
                del self._pool[bid]
            return len(idle)

    def _evict_one(self) -> str | None:
        """Evict the oldest idle disconnected entry; return broker_id or None."""
        candidates = [
            (bid, entry)
            for bid, entry in self._pool.items()
            if not entry.connection.is_connected()
        ]
        if not candidates:
            return None
        oldest_bid = min(candidates, key=lambda x: x[1].last_used)[0]
        del self._pool[oldest_bid]
        logger.debug("ConnectionPool: evicted idle broker %s", oldest_bid)
        return oldest_bid

    def statistics(self) -> dict[str, Any]:
        with self._lock:
            connected = sum(
                1 for e in self._pool.values() if e.connection.is_connected()
            )
            return {
                "total_slots":   len(self._pool),
                "connected":     connected,
                "disconnected":  len(self._pool) - connected,
                "max_capacity":  self._max_connections,
            }
