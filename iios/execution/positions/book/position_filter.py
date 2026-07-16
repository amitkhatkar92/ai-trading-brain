"""iios/execution/positions/book/position_filter.py
==================================================
Predicate-based filtering for the Position Book.

Provides a ``PositionPredicate`` type alias, built-in filter factories,
and a ``FilterChain`` class for composing multiple predicates.

C6 Execution Intelligence — Phase 3, Module 3
"""
from __future__ import annotations

from decimal import Decimal
from typing import Callable, List

from iios.execution.positions.lifecycle import (
    ACTIVE_STATES,
    CLOSED_STATES,
    TERMINAL_STATES,
    Position,
    PositionDirection,
    PositionProduct,
    PositionState,
)

# ── Type alias ────────────────────────────────────────────────────────────────

PositionPredicate = Callable[[Position], bool]


# ── Built-in filter factories ─────────────────────────────────────────────────

def active_filter() -> PositionPredicate:
    """Match positions in any active state."""
    return lambda p: p.state in ACTIVE_STATES


def closed_filter() -> PositionPredicate:
    """Match positions in any closed (non-archived) state."""
    return lambda p: p.state in CLOSED_STATES and p.state not in TERMINAL_STATES


def archived_filter() -> PositionPredicate:
    """Match positions in the ARCHIVED terminal state."""
    return lambda p: p.state in TERMINAL_STATES


def state_filter(state: PositionState) -> PositionPredicate:
    """Match positions in the exact *state*."""
    return lambda p: p.state == state


def instrument_filter(instrument: str) -> PositionPredicate:
    """Match positions on *instrument*."""
    return lambda p: p.instrument == instrument


def exchange_filter(exchange: str) -> PositionPredicate:
    """Match positions on *exchange*."""
    return lambda p: p.exchange == exchange


def portfolio_filter(portfolio_id: str) -> PositionPredicate:
    """Match positions belonging to *portfolio_id*."""
    return lambda p: p.portfolio_id == portfolio_id


def strategy_filter(strategy_id: str) -> PositionPredicate:
    """Match positions belonging to *strategy_id*."""
    return lambda p: p.strategy_id == strategy_id


def decision_filter(decision_id: str) -> PositionPredicate:
    """Match positions originating from *decision_id*."""
    return lambda p: p.decision_id == decision_id


def execution_filter(execution_id: str) -> PositionPredicate:
    """Match positions linked to *execution_id*."""
    return lambda p: p.execution_id == execution_id


def workflow_filter(workflow_id: str) -> PositionPredicate:
    """Match positions belonging to *workflow_id*."""
    return lambda p: p.workflow_id == workflow_id


def direction_filter(direction: PositionDirection) -> PositionPredicate:
    """Match positions with the given *direction*."""
    return lambda p: p.direction == direction


def product_filter(product: PositionProduct) -> PositionPredicate:
    """Match positions of the given *product* type."""
    return lambda p: p.product == product


def min_quantity_filter(minimum: Decimal) -> PositionPredicate:
    """Match positions whose total quantity >= *minimum*."""
    return lambda p: p.quantity >= minimum


def max_quantity_filter(maximum: Decimal) -> PositionPredicate:
    """Match positions whose total quantity <= *maximum*."""
    return lambda p: p.quantity <= maximum


def long_filter() -> PositionPredicate:
    """Match LONG positions."""
    return direction_filter(PositionDirection.LONG)


def short_filter() -> PositionPredicate:
    """Match SHORT positions."""
    return direction_filter(PositionDirection.SHORT)


# ── FilterChain ───────────────────────────────────────────────────────────────

class FilterChain:
    """
    Composes multiple predicates into a single combined AND-filter.

    All predicates in the chain must match for a position to be included.
    Use ``FilterChain.any_of()`` or ``FilterChain.none_of()`` static
    helpers to build OR/NOR predicates.

    Example
    -------
    chain = FilterChain(active_filter(), instrument_filter("NIFTY50"))
    matches = chain.apply(all_positions)
    """

    def __init__(self, *predicates: PositionPredicate) -> None:
        self._predicates: List[PositionPredicate] = list(predicates)

    def and_filter(self, predicate: PositionPredicate) -> "FilterChain":
        """Add a predicate to the AND-chain.  Returns self for fluent chaining."""
        self._predicates.append(predicate)
        return self

    def matches(self, position: Position) -> bool:
        """Returns ``True`` iff ALL predicates in the chain match *position*."""
        return all(pred(position) for pred in self._predicates)

    def apply(self, positions: List[Position]) -> List[Position]:
        """Return the subset of *positions* for which all predicates match."""
        return [p for p in positions if self.matches(p)]

    def apply_entries(self, entries) -> list:
        """Return the subset of ``BookEntry`` objects whose position matches."""
        return [e for e in entries if self.matches(e.position)]

    def __call__(self, position: Position) -> bool:
        return self.matches(position)

    def __len__(self) -> int:
        return len(self._predicates)

    # ── Static combinators ────────────────────────────────────────────────────

    @staticmethod
    def any_of(*predicates: PositionPredicate) -> PositionPredicate:
        """Return a predicate that matches if ANY of *predicates* matches."""
        def _or(position: Position) -> bool:
            return any(pred(position) for pred in predicates)
        return _or

    @staticmethod
    def none_of(*predicates: PositionPredicate) -> PositionPredicate:
        """Return a predicate that matches if NONE of *predicates* matches."""
        def _nor(position: Position) -> bool:
            return not any(pred(position) for pred in predicates)
        return _nor

    @staticmethod
    def negate(predicate: PositionPredicate) -> PositionPredicate:
        """Return the logical negation of *predicate*."""
        return lambda p: not predicate(p)
