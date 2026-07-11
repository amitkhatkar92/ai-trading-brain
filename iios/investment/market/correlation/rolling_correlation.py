"""iios/investment/market/correlation/rolling_correlation.py
Maintains rolling windows of asset returns and computes correlation matrices
incrementally.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional

import numpy as np

from iios.investment.market.correlation.models import CorrelationMatrix
from iios.investment.market.correlation.correlation_estimator import CorrelationEstimator
from iios.investment.market.correlation.correlation_matrix import (
    build_correlation_matrix,
    empty_correlation_matrix,
)


class RollingCorrelationCalculator:
    """
    Maintains a rolling deque of returns per symbol and recomputes the
    full correlation matrix on each update.

    Parameters
    ----------
    window          : rolling window size (number of bars to retain)
    estimator       : correlation estimator to use
    min_observations: minimum observations before computing (default = 5)
    symbols         : optional pre-seeded symbol list
    """

    def __init__(
        self,
        window: int,
        estimator: CorrelationEstimator,
        min_observations: int = 5,
        symbols: Optional[List[str]] = None,
    ) -> None:
        self._window        = window
        self._estimator     = estimator
        self._min_obs       = max(min_observations, estimator.min_observations)
        self._histories: Dict[str, deque] = {}

        if symbols:
            for s in symbols:
                self._histories[s] = deque(maxlen=window)

    # ── Public API ─────────────────────────────────────────────────────────

    def update(
        self,
        returns: Dict[str, float],
        bar_index: int,
        timestamp: float,
    ) -> Optional[CorrelationMatrix]:
        """
        Ingest one bar of returns and return the updated CorrelationMatrix
        (or None if insufficient history).
        """
        for sym, ret in returns.items():
            if sym not in self._histories:
                self._histories[sym] = deque(maxlen=self._window)
            if ret is not None and not (isinstance(ret, float) and (
                    ret != ret)):  # NaN check
                self._histories[sym].append(float(ret))

        return self._compute(bar_index, timestamp)

    def history_length(self, symbol: str) -> int:
        """Current number of stored observations for a symbol."""
        return len(self._histories.get(symbol, []))

    def all_symbols(self) -> List[str]:
        return list(self._histories.keys())

    def get_returns(self, symbol: str) -> np.ndarray:
        h = self._histories.get(symbol)
        return np.array(list(h)) if h else np.array([])

    @property
    def window(self) -> int:
        return self._window

    @property
    def estimator(self) -> CorrelationEstimator:
        return self._estimator

    @estimator.setter
    def estimator(self, value: CorrelationEstimator) -> None:
        self._estimator = value

    # ── Internal ──────────────────────────────────────────────────────────

    def _compute(
        self, bar_index: int, timestamp: float
    ) -> Optional[CorrelationMatrix]:
        eligible = [
            s for s, h in self._histories.items()
            if len(h) >= self._min_obs
        ]
        if len(eligible) < 2:
            return None

        arrays = {s: np.array(list(self._histories[s])) for s in eligible}

        return build_correlation_matrix(
            symbols=eligible,
            return_arrays=arrays,
            estimator=self._estimator,
            window=self._window,
            bar_index=bar_index,
            timestamp=timestamp,
        )
