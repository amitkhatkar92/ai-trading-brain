"""iios/execution/gateway/brokers/broker_connection.py
==================================================
BrokerConnection and ConnectionPool — connection state tracking
for the Broker Abstraction Layer.

These classes track connection state transitions without implementing
any broker-specific I/O.

C6 Execution Intelligence — Phase 5, Module 3
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Iterator, List, Optional

from .constants import (
    ACTIVE_BROKER_STATUSES,
    READY_BROKER_STATUSES,
    TERMINAL_BROKER_STATUSES,
    BrokerStatus,
)
from .exceptions import BrokerConnectionError


# ── BrokerConnection ──────────────────────────────────────────────────────────

class BrokerConnection:
    """
    Thread-safe connection state tracker for a single broker connection.

    The connection object does NOT hold network sockets, handles, or
    credentials.  It only records the current BrokerStatus and
    timing metadata.

    Connection ID
    -------------
    Most brokers have one connection.  Brokers that separate order
    flow from market data may use multiple named connections
    (e.g. ``"orders"``, ``"data"``), managed by a ConnectionPool.
    """

    __slots__ = (
        "_broker_id",
        "_connection_id",
        "_state",
        "_connected_at",
        "_disconnected_at",
        "_last_heartbeat_at",
        "_reconnect_count",
        "_lock",
    )

    def __init__(
        self,
        broker_id:     str,
        connection_id: str = "default",
    ) -> None:
        self._broker_id         = broker_id
        self._connection_id     = connection_id
        self._state             = BrokerStatus.DISCONNECTED
        self._connected_at:     Optional[float] = None
        self._disconnected_at:  Optional[float] = None
        self._last_heartbeat_at: Optional[float] = None
        self._reconnect_count   = 0
        self._lock              = threading.RLock()

    # ── Identity ──────────────────────────────────────────────────────────────

    @property
    def broker_id(self) -> str:
        return self._broker_id

    @property
    def connection_id(self) -> str:
        return self._connection_id

    # ── State transitions ─────────────────────────────────────────────────────

    def _set_state(self, new_state: BrokerStatus) -> None:
        with self._lock:
            self._state = new_state

    def set_connecting(self) -> None:
        self._set_state(BrokerStatus.CONNECTING)

    def set_authenticating(self) -> None:
        self._set_state(BrokerStatus.AUTHENTICATING)

    def set_connected(self) -> None:
        with self._lock:
            self._state        = BrokerStatus.CONNECTED
            self._connected_at = time.time()

    def set_active(self) -> None:
        self._set_state(BrokerStatus.ACTIVE)

    def set_degraded(self) -> None:
        self._set_state(BrokerStatus.DEGRADED)

    def set_reconnecting(self) -> None:
        with self._lock:
            self._state = BrokerStatus.RECONNECTING
            self._reconnect_count += 1

    def set_disconnected(self) -> None:
        with self._lock:
            self._state              = BrokerStatus.DISCONNECTED
            self._disconnected_at    = time.time()

    def set_failed(self) -> None:
        with self._lock:
            self._state           = BrokerStatus.FAILED
            self._disconnected_at = time.time()

    def set_stopped(self) -> None:
        with self._lock:
            self._state           = BrokerStatus.STOPPED
            self._disconnected_at = time.time()

    def record_heartbeat(self) -> None:
        with self._lock:
            self._last_heartbeat_at = time.time()

    # ── Queries ───────────────────────────────────────────────────────────────

    @property
    def state(self) -> BrokerStatus:
        with self._lock:
            return self._state

    @property
    def is_connected(self) -> bool:
        """True when the connection is in any ACTIVE_BROKER_STATUS."""
        with self._lock:
            return self._state in ACTIVE_BROKER_STATUSES

    @property
    def is_ready(self) -> bool:
        """True when the connection is ready to accept orders (CONNECTED/ACTIVE/DEGRADED)."""
        with self._lock:
            return self._state in READY_BROKER_STATUSES

    @property
    def is_terminal(self) -> bool:
        """True when the connection is in a terminal state (FAILED/STOPPED)."""
        with self._lock:
            return self._state in TERMINAL_BROKER_STATUSES

    @property
    def connected_at(self) -> Optional[float]:
        with self._lock:
            return self._connected_at

    @property
    def disconnected_at(self) -> Optional[float]:
        with self._lock:
            return self._disconnected_at

    @property
    def last_heartbeat_at(self) -> Optional[float]:
        with self._lock:
            return self._last_heartbeat_at

    @property
    def reconnect_count(self) -> int:
        with self._lock:
            return self._reconnect_count

    @property
    def uptime_secs(self) -> float:
        """Seconds since last successful connection, or 0 if not connected."""
        with self._lock:
            if self._connected_at is None:
                return 0.0
            return time.time() - self._connected_at

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "broker_id":          self._broker_id,
                "connection_id":      self._connection_id,
                "state":              self._state.value,
                "connected_at":       self._connected_at,
                "disconnected_at":    self._disconnected_at,
                "last_heartbeat_at":  self._last_heartbeat_at,
                "reconnect_count":    self._reconnect_count,
                "is_ready":           self._state in READY_BROKER_STATUSES,
            }

    def __repr__(self) -> str:
        return (
            f"BrokerConnection("
            f"broker_id={self._broker_id!r}, "
            f"connection_id={self._connection_id!r}, "
            f"state={self._state.value!r}"
            f")"
        )


# ── ConnectionPool ────────────────────────────────────────────────────────────

class ConnectionPool:
    """
    Thread-safe pool of named BrokerConnection objects for a single broker.

    Most brokers use one connection (``"default"``).  Brokers that
    separate order routing from market data may register additional
    named connections.
    """

    def __init__(self, broker_id: str) -> None:
        self._broker_id   = broker_id
        self._connections: Dict[str, BrokerConnection] = {}
        self._lock        = threading.Lock()

    @property
    def broker_id(self) -> str:
        return self._broker_id

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add(
        self,
        connection_id: str = "default",
        *,
        replace: bool = False,
    ) -> BrokerConnection:
        """
        Create and add a named connection.

        Parameters
        ----------
        connection_id:
            Unique name within this pool (e.g. ``"orders"``, ``"data"``).
        replace:
            When True, silently replaces an existing connection with the
            same ID.  When False (default), raises BrokerConnectionError.
        """
        with self._lock:
            if connection_id in self._connections and not replace:
                raise BrokerConnectionError(
                    self._broker_id,
                    f"Connection '{connection_id}' already exists in pool.",
                )
            conn = BrokerConnection(self._broker_id, connection_id)
            self._connections[connection_id] = conn
        return conn

    def remove(self, connection_id: str) -> None:
        """Remove a named connection from the pool."""
        with self._lock:
            self._connections.pop(connection_id, None)

    def disconnect_all(self) -> None:
        """Mark all connections as DISCONNECTED."""
        with self._lock:
            for conn in self._connections.values():
                conn.set_disconnected()

    def stop_all(self) -> None:
        """Mark all connections as STOPPED."""
        with self._lock:
            for conn in self._connections.values():
                conn.set_stopped()

    # ── Queries ───────────────────────────────────────────────────────────────

    def get(self, connection_id: str = "default") -> BrokerConnection:
        """Return the named connection.  Raises BrokerConnectionError if absent."""
        with self._lock:
            conn = self._connections.get(connection_id)
        if conn is None:
            raise BrokerConnectionError(
                self._broker_id,
                f"Connection '{connection_id}' not found in pool.",
            )
        return conn

    def get_optional(self, connection_id: str = "default") -> Optional[BrokerConnection]:
        with self._lock:
            return self._connections.get(connection_id)

    def all_connections(self) -> List[BrokerConnection]:
        with self._lock:
            return list(self._connections.values())

    def is_any_ready(self) -> bool:
        """True if at least one connection is ready for orders."""
        with self._lock:
            return any(c.is_ready for c in self._connections.values())

    def ready_connections(self) -> List[BrokerConnection]:
        with self._lock:
            return [c for c in self._connections.values() if c.is_ready]

    def count(self) -> int:
        with self._lock:
            return len(self._connections)

    def __iter__(self) -> Iterator[BrokerConnection]:
        with self._lock:
            snapshot = list(self._connections.values())
        return iter(snapshot)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "broker_id":   self._broker_id,
                "connections": {cid: c.to_dict() for cid, c in self._connections.items()},
                "count":       len(self._connections),
                "any_ready":   any(c.is_ready for c in self._connections.values()),
            }
