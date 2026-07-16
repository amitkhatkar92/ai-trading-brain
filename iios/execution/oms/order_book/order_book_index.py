"""iios/execution/oms/order_book/order_book_index.py
==================================================
OrderBookIndex — multi-dimensional secondary index for fast
lookup of OrderBookEntry objects.

Supports: portfolio, strategy, decision, execution, workflow,
broker, instrument, exchange, status, order_type, side.

C6 Execution Intelligence — Phase 2, Module 2
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any

from iios.execution.oms.order_book.constants import BookEntryStatus


class OrderBookIndex:
    """
    Thread-safe secondary index for the Order Book.

    Maintains 12 named buckets. Each bucket maps a key to the
    set of order_ids that match that key.

    The index is updated in O(1) on add/remove and queried in O(k)
    where k is the number of matching entries.
    """

    DIMENSIONS = (
        "portfolio_id",
        "strategy_id",
        "decision_id",
        "execution_id",
        "workflow_id",
        "broker_id",
        "instrument",
        "exchange",
        "status",
        "order_type",
        "side",
    )

    def __init__(self) -> None:
        # dim_name → {key → {order_id}}
        self._buckets: dict[str, dict[str, set[str]]] = {
            dim: defaultdict(set) for dim in self.DIMENSIONS
        }
        self._lock = threading.RLock()

    # ── Mutation ──────────────────────────────────────────────────────────────

    def add(self, entry_dict: dict[str, Any]) -> None:
        """Add an entry to all applicable buckets."""
        order_id = entry_dict["order_id"]
        with self._lock:
            for dim in self.DIMENSIONS:
                key = entry_dict.get(dim, "")
                if key:
                    self._buckets[dim][str(key)].add(order_id)

    def remove(self, entry_dict: dict[str, Any]) -> None:
        """Remove an entry from all applicable buckets."""
        order_id = entry_dict["order_id"]
        with self._lock:
            for dim in self.DIMENSIONS:
                key = entry_dict.get(dim, "")
                if key:
                    bucket = self._buckets[dim].get(str(key))
                    if bucket:
                        bucket.discard(order_id)

    def update_status(
        self,
        order_id:   str,
        old_status: str,
        new_status: str,
    ) -> None:
        """Move an order_id from one status bucket to another."""
        with self._lock:
            if old_status:
                self._buckets["status"][old_status].discard(order_id)
            if new_status:
                self._buckets["status"][new_status].add(order_id)

    # ── Query ─────────────────────────────────────────────────────────────────

    def lookup(self, dimension: str, key: str) -> frozenset[str]:
        """Return all order_ids matching dimension=key."""
        with self._lock:
            bucket = self._buckets.get(dimension, {})
            return frozenset(bucket.get(str(key), set()))

    def lookup_all(self, dimension: str) -> dict[str, frozenset[str]]:
        """Return all key→{order_ids} for a dimension."""
        with self._lock:
            return {k: frozenset(v) for k, v in self._buckets[dimension].items()}

    def intersect(self, criteria: dict[str, str]) -> frozenset[str]:
        """Return order_ids matching ALL key=value pairs (AND query)."""
        if not criteria:
            return frozenset()
        sets = [self.lookup(dim, key) for dim, key in criteria.items()]
        result = sets[0]
        for s in sets[1:]:
            result = result & s
        return result

    # ── Statistics ────────────────────────────────────────────────────────────

    def cardinality(self, dimension: str) -> int:
        """Number of distinct keys in a dimension."""
        with self._lock:
            return len(self._buckets.get(dimension, {}))

    def utilization(self) -> dict[str, int]:
        """Per-dimension key counts."""
        with self._lock:
            return {dim: len(self._buckets[dim]) for dim in self.DIMENSIONS}

    def clear(self) -> None:
        with self._lock:
            for dim in self.DIMENSIONS:
                self._buckets[dim].clear()
