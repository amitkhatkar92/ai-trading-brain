"""iios/investment/market/correlation/estimator_registry.py
Thread-safe registry of CorrelationEstimator instances.
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional

from iios.investment.market.correlation.correlation_estimator import CorrelationEstimator


class EstimatorRegistry:
    def __init__(self) -> None:
        self._lock    = threading.Lock()
        self._estimators: Dict[str, CorrelationEstimator] = {}

    def register(self, estimator: CorrelationEstimator) -> None:
        with self._lock:
            self._estimators[estimator.name] = estimator

    def unregister(self, name: str) -> None:
        with self._lock:
            self._estimators.pop(name, None)

    def get(self, name: str) -> Optional[CorrelationEstimator]:
        with self._lock:
            return self._estimators.get(name)

    def all(self) -> List[CorrelationEstimator]:
        with self._lock:
            return list(self._estimators.values())

    def names(self) -> List[str]:
        with self._lock:
            return list(self._estimators.keys())

    def default(self) -> Optional[CorrelationEstimator]:
        """Return the first registered estimator (typically Pearson)."""
        with self._lock:
            if not self._estimators:
                return None
            return next(iter(self._estimators.values()))

    def __len__(self) -> int:
        with self._lock:
            return len(self._estimators)
