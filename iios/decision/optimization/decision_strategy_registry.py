"""
decision_strategy_registry.py — iios.decision.optimization
===========================================================
Thread-safe registry for DecisionOptimizationStrategy objects.

C9 Decision Intelligence — Phase 1, Module 4
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from .constants import DEFAULT_MAX_STRATEGIES, DEFAULT_STRATEGY_ID, OptimizationStrategyType
from .decision_optimization_strategy import DecisionOptimizationStrategy
from .exceptions import StrategyNotFoundError


class DecisionStrategyRegistry:
    """
    Thread-safe registry for :class:`DecisionOptimizationStrategy` objects.

    A default WEIGHTED_SCORE strategy is registered at construction time
    with id ``DEFAULT_STRATEGY_ID``.

    Parameters
    ----------
    max_strategies : Maximum strategies the registry accepts.
    """

    def __init__(self, max_strategies: int = DEFAULT_MAX_STRATEGIES) -> None:
        self._lock       = threading.RLock()
        self._strategies: Dict[str, DecisionOptimizationStrategy] = {}
        self._max        = max_strategies
        # Register default
        default = DecisionOptimizationStrategy.weighted_score(strategy_id=DEFAULT_STRATEGY_ID)
        self._strategies[DEFAULT_STRATEGY_ID] = default

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def register(self, strategy: DecisionOptimizationStrategy) -> None:
        with self._lock:
            if (len(self._strategies) >= self._max
                    and strategy.strategy_id not in self._strategies):
                raise StrategyNotFoundError(
                    f"Strategy registry is full (max {self._max})"
                )
            self._strategies[strategy.strategy_id] = strategy

    def deregister(self, strategy_id: str) -> Optional[DecisionOptimizationStrategy]:
        with self._lock:
            return self._strategies.pop(strategy_id, None)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, strategy_id: str) -> DecisionOptimizationStrategy:
        with self._lock:
            if strategy_id not in self._strategies:
                raise StrategyNotFoundError(strategy_id)
            return self._strategies[strategy_id]

    def find(self, strategy_id: str) -> Optional[DecisionOptimizationStrategy]:
        with self._lock:
            return self._strategies.get(strategy_id)

    def get_default(self) -> DecisionOptimizationStrategy:
        return self.get(DEFAULT_STRATEGY_ID)

    def all_strategies(self) -> List[DecisionOptimizationStrategy]:
        with self._lock:
            return list(self._strategies.values())

    def count(self) -> int:
        with self._lock:
            return len(self._strategies)
