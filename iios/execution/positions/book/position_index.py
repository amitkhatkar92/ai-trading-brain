"""iios/execution/positions/book/position_index.py
==================================================
PositionIndex — multi-key index system for the Position Book.

Maintains 11 concurrent indexes over BookEntry objects to support
O(1) primary lookups and O(k) secondary lookups (where k is the
result set size for the given key).

Index contract
--------------
add(entry)               — register entry in all 11 indexes
remove(entry)            — de-register entry from all 11 indexes
reindex_state(entry, old_state) — refresh only LIFECYCLE_STATE index
                           after a position transitions state

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import threading
from collections import defaultdict
from typing import Dict, List, Optional, Set

from iios.execution.positions.lifecycle import (
    ACTIVE_STATES,
    CLOSED_STATES,
    SUSPENDED_STATES,
    TERMINAL_STATES,
    PositionState,
)

from .constants import IndexType
from .exceptions import PositionBookIndexError
from .position_entry import BookEntry


class PositionIndex:
    """
    Thread-safe multi-key index over ``BookEntry`` objects.

    Primary index
    ~~~~~~~~~~~~~
    ``position_id`` → ``BookEntry``  (O(1))

    Secondary indexes (key → Set[position_id])
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    portfolio_id, strategy_id, decision_id, execution_id, workflow_id,
    instrument, exchange, product, direction, lifecycle_state

    All read/write operations are serialised through a single
    ``threading.RLock`` to ensure consistency across the 11 indexes.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

        # Primary: position_id → BookEntry
        self._primary: Dict[str, BookEntry] = {}

        # Secondary: index_key → Set[position_id]
        self._by_portfolio:  Dict[str, Set[str]] = defaultdict(set)
        self._by_strategy:   Dict[str, Set[str]] = defaultdict(set)
        self._by_decision:   Dict[str, Set[str]] = defaultdict(set)
        self._by_execution:  Dict[str, Set[str]] = defaultdict(set)
        self._by_workflow:   Dict[str, Set[str]] = defaultdict(set)
        self._by_instrument: Dict[str, Set[str]] = defaultdict(set)
        self._by_exchange:   Dict[str, Set[str]] = defaultdict(set)
        self._by_product:    Dict[str, Set[str]] = defaultdict(set)
        self._by_direction:  Dict[str, Set[str]] = defaultdict(set)
        self._by_state:      Dict[str, Set[str]] = defaultdict(set)

        # Per-index utilization counters
        self._utilization: Dict[IndexType, int] = {t: 0 for t in IndexType}

    # ── Write ─────────────────────────────────────────────────────────────────

    def add(self, entry: BookEntry) -> None:
        """
        Register *entry* in all 11 indexes.

        Raises ``PositionBookIndexError`` if the position_id is already indexed.
        """
        pid = entry.position_id
        with self._lock:
            if pid in self._primary:
                raise PositionBookIndexError(
                    f"Position '{pid}' is already indexed",
                    index_type=IndexType.POSITION_ID,
                )
            self._primary[pid] = entry
            self._by_portfolio[entry.portfolio_id].add(pid)
            self._by_strategy[entry.strategy_id].add(pid)
            self._by_decision[entry.decision_id].add(pid)
            self._by_execution[entry.execution_id].add(pid)
            self._by_workflow[entry.workflow_id].add(pid)
            self._by_instrument[entry.instrument].add(pid)
            self._by_exchange[entry.exchange].add(pid)
            self._by_product[entry.product.value].add(pid)
            self._by_direction[entry.direction.value].add(pid)
            self._by_state[entry.state.value].add(pid)

    def remove(self, entry: BookEntry) -> None:
        """
        Remove *entry* from all 11 indexes.  Idempotent if not present.
        """
        pid = entry.position_id
        with self._lock:
            if pid not in self._primary:
                return
            del self._primary[pid]
            self._by_portfolio[entry.portfolio_id].discard(pid)
            self._by_strategy[entry.strategy_id].discard(pid)
            self._by_decision[entry.decision_id].discard(pid)
            self._by_execution[entry.execution_id].discard(pid)
            self._by_workflow[entry.workflow_id].discard(pid)
            self._by_instrument[entry.instrument].discard(pid)
            self._by_exchange[entry.exchange].discard(pid)
            self._by_product[entry.product.value].discard(pid)
            self._by_direction[entry.direction.value].discard(pid)
            self._by_state[entry.state.value].discard(pid)

    def reindex_state(self, entry: BookEntry, old_state: PositionState) -> None:
        """
        Refresh the LIFECYCLE_STATE index after a position transition.

        The caller must invoke this *after* the Position's state has
        already been updated, so ``entry.state`` reflects the new state.
        """
        pid = entry.position_id
        with self._lock:
            self._by_state[old_state.value].discard(pid)
            self._by_state[entry.state.value].add(pid)
            self._utilization[IndexType.LIFECYCLE_STATE] += 1

    # ── Primary lookup ────────────────────────────────────────────────────────

    def get(self, position_id: str) -> Optional[BookEntry]:
        """O(1) primary index lookup.  Returns ``None`` if not found."""
        with self._lock:
            self._utilization[IndexType.POSITION_ID] += 1
            return self._primary.get(position_id)

    def contains(self, position_id: str) -> bool:
        with self._lock:
            return position_id in self._primary

    def count(self) -> int:
        with self._lock:
            return len(self._primary)

    def all(self) -> List[BookEntry]:
        """All registered entries, in arbitrary insertion order."""
        with self._lock:
            return list(self._primary.values())

    # ── Secondary lookups ─────────────────────────────────────────────────────

    def _resolve(self, ids: Set[str], index_type: IndexType) -> List[BookEntry]:
        """Resolve a set of position_ids to BookEntry objects."""
        with self._lock:
            self._utilization[index_type] += 1
            return [self._primary[pid] for pid in ids if pid in self._primary]

    def by_portfolio(self, portfolio_id: str) -> List[BookEntry]:
        with self._lock:
            ids = set(self._by_portfolio.get(portfolio_id, set()))
        return self._resolve(ids, IndexType.PORTFOLIO_ID)

    def by_strategy(self, strategy_id: str) -> List[BookEntry]:
        with self._lock:
            ids = set(self._by_strategy.get(strategy_id, set()))
        return self._resolve(ids, IndexType.STRATEGY_ID)

    def by_decision(self, decision_id: str) -> List[BookEntry]:
        with self._lock:
            ids = set(self._by_decision.get(decision_id, set()))
        return self._resolve(ids, IndexType.DECISION_ID)

    def by_execution(self, execution_id: str) -> List[BookEntry]:
        with self._lock:
            ids = set(self._by_execution.get(execution_id, set()))
        return self._resolve(ids, IndexType.EXECUTION_ID)

    def by_workflow(self, workflow_id: str) -> List[BookEntry]:
        with self._lock:
            ids = set(self._by_workflow.get(workflow_id, set()))
        return self._resolve(ids, IndexType.WORKFLOW_ID)

    def by_instrument(self, instrument: str) -> List[BookEntry]:
        with self._lock:
            ids = set(self._by_instrument.get(instrument, set()))
        return self._resolve(ids, IndexType.INSTRUMENT)

    def by_exchange(self, exchange: str) -> List[BookEntry]:
        with self._lock:
            ids = set(self._by_exchange.get(exchange, set()))
        return self._resolve(ids, IndexType.EXCHANGE)

    def by_product(self, product_value: str) -> List[BookEntry]:
        with self._lock:
            ids = set(self._by_product.get(product_value, set()))
        return self._resolve(ids, IndexType.PRODUCT)

    def by_direction(self, direction_value: str) -> List[BookEntry]:
        with self._lock:
            ids = set(self._by_direction.get(direction_value, set()))
        return self._resolve(ids, IndexType.DIRECTION)

    def by_state(self, state: PositionState) -> List[BookEntry]:
        with self._lock:
            ids = set(self._by_state.get(state.value, set()))
        return self._resolve(ids, IndexType.LIFECYCLE_STATE)

    def active(self) -> List[BookEntry]:
        """Entries in any active state (OPENING / OPEN / PARTIALLY_CLOSED / CLOSING)."""
        result: List[BookEntry] = []
        with self._lock:
            self._utilization[IndexType.LIFECYCLE_STATE] += 1
            for s in ACTIVE_STATES:
                for pid in self._by_state.get(s.value, set()):
                    if pid in self._primary:
                        result.append(self._primary[pid])
        return result

    def closed(self) -> List[BookEntry]:
        """Entries in CLOSED state (not yet archived)."""
        result: List[BookEntry] = []
        with self._lock:
            self._utilization[IndexType.LIFECYCLE_STATE] += 1
            for s in CLOSED_STATES:
                if s in TERMINAL_STATES:
                    continue
                for pid in self._by_state.get(s.value, set()):
                    if pid in self._primary:
                        result.append(self._primary[pid])
        return result

    def archived(self) -> List[BookEntry]:
        """Entries in the ARCHIVED terminal state."""
        result: List[BookEntry] = []
        with self._lock:
            self._utilization[IndexType.LIFECYCLE_STATE] += 1
            for s in TERMINAL_STATES:
                for pid in self._by_state.get(s.value, set()):
                    if pid in self._primary:
                        result.append(self._primary[pid])
        return result

    def suspended(self) -> List[BookEntry]:
        """Entries in any suspended state."""
        result: List[BookEntry] = []
        with self._lock:
            self._utilization[IndexType.LIFECYCLE_STATE] += 1
            for s in SUSPENDED_STATES:
                for pid in self._by_state.get(s.value, set()):
                    if pid in self._primary:
                        result.append(self._primary[pid])
        return result

    # ── Utilization ───────────────────────────────────────────────────────────

    def utilization(self) -> Dict[IndexType, int]:
        """Returns a copy of the index utilization counters."""
        with self._lock:
            return dict(self._utilization)

    def reset_utilization(self) -> None:
        """Reset all utilization counters to zero."""
        with self._lock:
            for k in self._utilization:
                self._utilization[k] = 0
