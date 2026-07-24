"""
connection_pool.py — iios.integration.services
------------------------------------------------
ConnectionPool — bounded pool of reusable connector slots for
integration services.

C15 Enterprise Integration & Connectivity — Phase 1, Module 4
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from iios.common.logging.logging_manager import get_logger

from .constants import DEFAULT_POOL_MAX, DEFAULT_POOL_SIZE, ConnectionState

_log = get_logger(__name__)


@dataclass
class PoolSlot:
    """A single slot in the connection pool."""
    slot_id:      str
    pool_name:    str
    state:        ConnectionState
    acquired_at:  Optional[str] = None
    released_at:  Optional[str] = None
    uses:         int = 0


@dataclass
class PoolStats:
    """Connection pool statistics snapshot."""
    pool_name:   str
    total_slots: int
    available:   int
    in_use:      int
    wait_count:  int
    total_acquires: int
    total_releases: int


class ConnectionPool:
    """
    Bounded connection slot pool with acquire/release semantics.

    ``acquire()`` returns a PoolSlot within timeout_ms or raises.
    ``release()`` returns the slot to the pool.

    Slots are lightweight placeholders; actual connection objects are
    managed by the vendor adapter that wraps the slot.
    """

    def __init__(
        self,
        pool_name: str,
        min_size:  int = DEFAULT_POOL_SIZE,
        max_size:  int = DEFAULT_POOL_MAX,
    ) -> None:
        self._name      = pool_name
        self._lock      = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._min       = min(min_size, max_size)
        self._max       = max_size
        self._available: List[PoolSlot]      = []
        self._in_use:    Dict[str, PoolSlot] = {}
        self._total_acquires = 0
        self._total_releases = 0
        self._wait_count     = 0

        # Pre-create min_size slots
        for _ in range(self._min):
            self._available.append(self._new_slot())

    # ── Public ───────────────────────────────────────────────────────────

    def acquire(self, timeout_ms: int = 5_000) -> PoolSlot:
        """
        Acquire a pool slot. Blocks up to timeout_ms.
        Raises RuntimeError if pool is exhausted and no slot becomes available.
        """
        deadline = time.monotonic() + (timeout_ms / 1_000)
        with self._condition:
            while True:
                if self._available:
                    slot = self._available.pop()
                    slot.state       = ConnectionState.CONNECTED
                    slot.acquired_at = datetime.now(timezone.utc).isoformat()
                    slot.uses       += 1
                    self._in_use[slot.slot_id] = slot
                    self._total_acquires += 1
                    return slot

                total = len(self._available) + len(self._in_use)
                if total < self._max:
                    slot = self._new_slot()
                    slot.state       = ConnectionState.CONNECTED
                    slot.acquired_at = datetime.now(timezone.utc).isoformat()
                    slot.uses       += 1
                    self._in_use[slot.slot_id] = slot
                    self._total_acquires += 1
                    return slot

                # Pool full — wait
                self._wait_count += 1
                remaining_s = deadline - time.monotonic()
                if remaining_s <= 0:
                    self._wait_count -= 1
                    raise RuntimeError(
                        f"connection-pool {self._name!r}: "
                        f"acquire timed out after {timeout_ms} ms"
                    )
                self._condition.wait(timeout=remaining_s)
                self._wait_count -= 1

    def release(self, slot: PoolSlot) -> None:
        """Return a slot to the available pool."""
        with self._condition:
            if slot.slot_id in self._in_use:
                del self._in_use[slot.slot_id]
            slot.state       = ConnectionState.IDLE
            slot.released_at = datetime.now(timezone.utc).isoformat()
            self._available.append(slot)
            self._total_releases += 1
            self._condition.notify()

    def invalidate(self, slot: PoolSlot) -> None:
        """Permanently remove a slot from the pool (e.g. after error)."""
        with self._condition:
            self._in_use.pop(slot.slot_id, None)
            slot.state = ConnectionState.FAILED
            self._condition.notify()

    # ── Stats ─────────────────────────────────────────────────────────────

    def stats(self) -> PoolStats:
        with self._lock:
            return PoolStats(
                pool_name      = self._name,
                total_slots    = len(self._available) + len(self._in_use),
                available      = len(self._available),
                in_use         = len(self._in_use),
                wait_count     = self._wait_count,
                total_acquires = self._total_acquires,
                total_releases = self._total_releases,
            )

    @property
    def name(self) -> str:
        return self._name

    # ── Internals ─────────────────────────────────────────────────────────

    def _new_slot(self) -> PoolSlot:
        return PoolSlot(
            slot_id   = f"cpool-{uuid.uuid4().hex[:10]}",
            pool_name = self._name,
            state     = ConnectionState.IDLE,
        )
