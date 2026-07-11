"""iios/investment/market/volatility/estimator_registry.py
Thread-safe registry of VolatilityEstimator instances.

Allows adding, removing and querying estimators at runtime without modifying
any core engine code.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, TYPE_CHECKING

from iios.investment.market.volatility.volatility_estimator import VolatilityEstimator

if TYPE_CHECKING:
    pass


class EstimatorRegistry:
    """Manages a collection of pluggable volatility estimators."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._estimators: Dict[str, VolatilityEstimator] = {}

    def register(self, estimator: VolatilityEstimator) -> None:
        """Register an estimator, replacing any existing entry with the same name."""
        with self._lock:
            self._estimators[estimator.name] = estimator

    def unregister(self, name: str) -> None:
        """Remove an estimator by name.  Silent if not found."""
        with self._lock:
            self._estimators.pop(name, None)

    def get(self, name: str) -> Optional[VolatilityEstimator]:
        with self._lock:
            return self._estimators.get(name)

    def all(self) -> List[VolatilityEstimator]:
        with self._lock:
            return list(self._estimators.values())

    def names(self) -> List[str]:
        with self._lock:
            return list(self._estimators.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._estimators)
