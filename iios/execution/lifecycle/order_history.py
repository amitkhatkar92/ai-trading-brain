"""iios/execution/lifecycle/order_history.py
==================================================
OrderHistory — append-only, thread-safe sequence of
OrderTransition records for a single order.

History entries are never modified or removed.
A ring-buffer cap (max_entries) prevents unbounded
growth on very long-lived orders; when exceeded the
oldest entries are evicted and evicted_count is
incremented for observability.
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Iterator, Optional, Tuple

from .order_state import OrderState
from .order_transition import OrderTransition


class OrderHistory:
    """
    Append-only, thread-safe transition history for one order.

    Parameters
    ----------
    order_id : str
        The order this history belongs to.
    max_entries : int
        Maximum retained entries (default 1 000).
    """

    __slots__ = ("_order_id", "_max_entries", "_entries", "_lock",
                 "_total", "_evicted")

    def __init__(self, order_id: str, max_entries: int = 1_000) -> None:
        self._order_id:    str                       = order_id
        self._max_entries: int                       = max(1, max_entries)
        self._entries:     deque[OrderTransition]    = deque(maxlen=self._max_entries)
        self._lock:        threading.Lock            = threading.Lock()
        self._total:       int                       = 0  # ever-increasing
        self._evicted:     int                       = 0

    # ── Write ──────────────────────────────────────────────────────────────────

    def record(self, transition: OrderTransition) -> None:
        """
        Append *transition* to the history.  Thread-safe.

        Raises
        ------
        ValueError
            If transition.order_id does not match this history's order_id.
        """
        if transition.order_id != self._order_id:
            raise ValueError(
                f"OrderHistory.record: transition order_id "
                f"{transition.order_id!r} != history order_id {self._order_id!r}."
            )
        with self._lock:
            if len(self._entries) == self._max_entries:
                self._evicted += 1
            self._entries.append(transition)
            self._total += 1

    # ── Read ───────────────────────────────────────────────────────────────────

    def entries(self) -> Tuple[OrderTransition, ...]:
        """Snapshot of all retained entries, oldest first."""
        with self._lock:
            return tuple(self._entries)

    def last(self) -> Optional[OrderTransition]:
        """Most recent transition, or None if the history is empty."""
        with self._lock:
            return self._entries[-1] if self._entries else None

    def first(self) -> Optional[OrderTransition]:
        """Oldest retained transition, or None if the history is empty."""
        with self._lock:
            return self._entries[0] if self._entries else None

    def count(self) -> int:
        """Number of entries currently retained (≤ max_entries)."""
        with self._lock:
            return len(self._entries)

    @property
    def total_recorded(self) -> int:
        """Total transitions ever appended, including evicted ones."""
        return self._total

    @property
    def evicted_count(self) -> int:
        """Number of entries dropped due to the max_entries cap."""
        return self._evicted

    def states_visited(self) -> frozenset[OrderState]:
        """Set of all to_state values recorded in the retained history."""
        with self._lock:
            return frozenset(t.to_state for t in self._entries)

    def __iter__(self) -> Iterator[OrderTransition]:
        return iter(self.entries())

    def __len__(self) -> int:
        return self.count()

    def __repr__(self) -> str:
        return (
            f"OrderHistory(order_id={self._order_id!r}, "
            f"count={self.count()}, total={self._total})"
        )
