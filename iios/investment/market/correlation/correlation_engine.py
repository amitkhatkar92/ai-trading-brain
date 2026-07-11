"""iios/investment/market/correlation/correlation_engine.py
Core correlation engine: orchestrates rolling window calculations and
supports multiple simultaneous estimators (multi-method analysis).
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from iios.investment.market.correlation.models import (
    CorrelationMatrix,
    CorrelationMethod,
    MultiAssetSnapshot,
)
from iios.investment.market.correlation.correlation_estimator import CorrelationEstimator
from iios.investment.market.correlation.estimator_registry import EstimatorRegistry
from iios.investment.market.correlation.rolling_correlation import RollingCorrelationCalculator
from iios.investment.market.correlation.correlation_statistics import CorrelationStatistics
from iios.investment.market.correlation.pearson_estimator import PearsonEstimator


class CorrelationEngine:
    """
    Orchestrates rolling pairwise correlation computation.

    Maintains one RollingCorrelationCalculator per registered estimator.
    The primary estimator (default: Pearson) drives the main CorrelationMatrix.
    """

    def __init__(
        self,
        window:           int = 60,
        min_observations: int = 10,
        primary_estimator: Optional[CorrelationEstimator] = None,
        registry:         Optional[EstimatorRegistry] = None,
    ) -> None:
        self._window          = window
        self._min_obs         = min_observations
        self._primary         = primary_estimator or PearsonEstimator()
        self._registry        = registry or EstimatorRegistry()
        self._registry.register(self._primary)

        self._calculators: Dict[str, RollingCorrelationCalculator] = {
            self._primary.name: RollingCorrelationCalculator(
                window=window,
                estimator=self._primary,
                min_observations=min_observations,
            )
        }
        self._stats  = CorrelationStatistics(window=50)
        self._current: Optional[CorrelationMatrix] = None

    # ── Public API ─────────────────────────────────────────────────────────

    def update(
        self, snapshot: MultiAssetSnapshot
    ) -> Optional[CorrelationMatrix]:
        """
        Process one MultiAssetSnapshot and return the updated primary
        CorrelationMatrix.
        """
        returns = {
            obs.symbol: obs.return_pct
            for obs in snapshot.observations
            if obs.return_pct is not None
        }

        primary_calc = self._calculators[self._primary.name]
        matrix = primary_calc.update(
            returns, snapshot.bar_index, snapshot.timestamp
        )

        if matrix is not None:
            self._stats.update(matrix)
            self._current = matrix

        # Update additional estimators in parallel (non-blocking)
        for name, calc in self._calculators.items():
            if name != self._primary.name:
                calc.update(returns, snapshot.bar_index, snapshot.timestamp)

        return matrix

    def current_matrix(self) -> Optional[CorrelationMatrix]:
        return self._current

    def statistics(self) -> CorrelationStatistics:
        return self._stats

    def register_estimator(self, estimator: CorrelationEstimator) -> None:
        self._registry.register(estimator)
        if estimator.name not in self._calculators:
            self._calculators[estimator.name] = RollingCorrelationCalculator(
                window=self._window,
                estimator=estimator,
                min_observations=self._min_obs,
            )

    def unregister_estimator(self, name: str) -> None:
        if name == self._primary.name:
            return  # never remove primary
        self._registry.unregister(name)
        self._calculators.pop(name, None)

    def get_matrix_by_method(
        self, method: CorrelationMethod, bar_index: int, timestamp: float
    ) -> Optional[CorrelationMatrix]:
        """Return a freshly-computed matrix using a specific method."""
        estimator = next(
            (e for e in self._registry.all() if e.method == method), None
        )
        if estimator is None:
            return None
        calc = self._calculators.get(estimator.name)
        if calc is None:
            return None
        returns = {
            s: float(calc.get_returns(s)[-1])
            for s in calc.all_symbols()
            if len(calc.get_returns(s)) > 0
        }
        return calc.update(returns, bar_index, timestamp)

    def get_returns(self, symbol: str) -> np.ndarray:
        calc = self._calculators.get(self._primary.name)
        if calc is None:
            return np.array([])
        return calc.get_returns(symbol)

    def all_symbols(self) -> List[str]:
        calc = self._calculators.get(self._primary.name)
        return calc.all_symbols() if calc else []
