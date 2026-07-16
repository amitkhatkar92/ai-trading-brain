"""iios/execution/positions/book/position_query.py
==================================================
BookQuery  — structured query type for the Position Book.
QueryResult — immutable result container returned by PositionBook.find().

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from iios.execution.positions.lifecycle import (
    PositionDirection,
    PositionProduct,
    PositionState,
)

from .constants import BookOperationType, DEFAULT_QUERY_LIMIT
from .position_filter import PositionPredicate

if TYPE_CHECKING:
    from .position_entry import BookEntry


@dataclass
class BookQuery:
    """
    Structured query for the Position Book.

    All fields are optional; unset fields (None) are treated as wildcards.
    The ``custom_filter`` predicate is applied after all field filters.

    ``position_id`` short-circuits all other filters when set alone.
    ``limit`` caps the result size.
    """

    # Primary lookup
    position_id:   Optional[str]               = None

    # Identity filters
    portfolio_id:  Optional[str]               = None
    strategy_id:   Optional[str]               = None
    decision_id:   Optional[str]               = None
    execution_id:  Optional[str]               = None
    workflow_id:   Optional[str]               = None

    # Instrument filters
    instrument:    Optional[str]               = None
    exchange:      Optional[str]               = None
    product:       Optional[PositionProduct]   = None
    direction:     Optional[PositionDirection] = None

    # Lifecycle filter
    state:         Optional[PositionState]     = None

    # Custom predicate (applied last, after all field filters)
    custom_filter: Optional[PositionPredicate] = None

    # Result cap
    limit:         int                         = DEFAULT_QUERY_LIMIT

    # ── Derived ───────────────────────────────────────────────────────────────

    @property
    def is_single_lookup(self) -> bool:
        """True when only position_id is set — served from primary index."""
        return (
            self.position_id is not None and
            all(v is None for v in (
                self.portfolio_id, self.strategy_id, self.decision_id,
                self.execution_id, self.workflow_id, self.instrument,
                self.exchange, self.product, self.direction,
                self.state, self.custom_filter,
            ))
        )

    @property
    def is_empty(self) -> bool:
        """True when no filter is set — matches all positions."""
        return all(v is None for v in (
            self.position_id, self.portfolio_id, self.strategy_id,
            self.decision_id, self.execution_id, self.workflow_id,
            self.instrument, self.exchange, self.product, self.direction,
            self.state, self.custom_filter,
        ))

    @property
    def is_index_query(self) -> bool:
        """
        True when exactly one secondary filter is set without a custom filter —
        can be served from a single secondary index without a full scan.
        """
        if self.custom_filter is not None or self.position_id is not None:
            return False
        field_filters = [
            self.portfolio_id, self.strategy_id, self.decision_id,
            self.execution_id, self.workflow_id, self.instrument,
            self.exchange, self.product, self.direction, self.state,
        ]
        return sum(1 for f in field_filters if f is not None) == 1


@dataclass(frozen=True)
class QueryResult:
    """
    Immutable result container returned by ``PositionBook.find()``.
    """

    query_id:    str
    entries:     Tuple  # Tuple[BookEntry, ...]
    elapsed_ms:  float
    executed_at: float

    @property
    def count(self) -> int:
        return len(self.entries)

    @property
    def is_empty(self) -> bool:
        return len(self.entries) == 0

    @property
    def positions(self) -> List:
        """Convenience: list of live Position objects from the matched entries."""
        return [e.position for e in self.entries]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query_id":    self.query_id,
            "count":       self.count,
            "elapsed_ms":  self.elapsed_ms,
            "executed_at": self.executed_at,
        }


def make_query_result(
    entries:    List["BookEntry"],
    elapsed_ms: float,
) -> QueryResult:
    return QueryResult(
        query_id=str(uuid.uuid4()),
        entries=tuple(entries),
        elapsed_ms=elapsed_ms,
        executed_at=time.time(),
    )
