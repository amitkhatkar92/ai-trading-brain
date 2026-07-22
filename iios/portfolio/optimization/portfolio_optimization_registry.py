"""
portfolio_optimization_registry.py — iios.portfolio.optimization
=================================================================
Thread-safe, bounded store for completed optimization run results.

C10 Portfolio Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_OPTIMIZATIONS
from .exceptions import (
    PortfolioOptimizationCapacityError,
    PortfolioOptimizationNotFoundError,
)
from .portfolio_optimization_response import PortfolioOptimizationResponse


class PortfolioOptimizationRegistry:
    """
    Thread-safe, bounded store for PortfolioOptimizationResponse objects.

    Indexed by ``optimization_id`` for O(1) lookup.

    Parameters
    ----------
    max_optimizations : Hard upper bound on stored results.
    """

    def __init__(self, max_optimizations: int = DEFAULT_MAX_OPTIMIZATIONS) -> None:
        self._max   = max_optimizations
        self._store: Dict[str, PortfolioOptimizationResponse] = {}
        self._lock  = threading.Lock()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def register(self, response: PortfolioOptimizationResponse) -> None:
        """Store an optimization result."""
        with self._lock:
            if (
                len(self._store) >= self._max
                and response.optimization_id not in self._store
            ):
                raise PortfolioOptimizationCapacityError(
                    self._max, resource="optimization registry"
                )
            self._store[response.optimization_id] = response

    def remove(self, optimization_id: str) -> None:
        with self._lock:
            if optimization_id not in self._store:
                raise PortfolioOptimizationNotFoundError(
                    optimization_id, item_type="optimization"
                )
            del self._store[optimization_id]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, optimization_id: str) -> Optional[PortfolioOptimizationResponse]:
        with self._lock:
            return self._store.get(optimization_id)

    def get_or_raise(
        self, optimization_id: str
    ) -> PortfolioOptimizationResponse:
        result = self.get(optimization_id)
        if result is None:
            raise PortfolioOptimizationNotFoundError(
                optimization_id, item_type="optimization"
            )
        return result

    def for_portfolio(self, portfolio_id: str) -> List[PortfolioOptimizationResponse]:
        with self._lock:
            return [
                r for r in self._store.values()
                if r.portfolio_id == portfolio_id
            ]

    def all(self) -> List[PortfolioOptimizationResponse]:
        with self._lock:
            return list(self._store.values())

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._store)

    def __contains__(self, optimization_id: str) -> bool:
        with self._lock:
            return optimization_id in self._store
