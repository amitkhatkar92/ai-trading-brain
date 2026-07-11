"""iios/investment/market/correlation/correlation_statistics.py
Rolling statistics about the time evolution of correlations.
"""
from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np

from iios.investment.market.correlation.models import CorrelationMatrix


class CorrelationStatistics:
    """
    Tracks rolling statistics over the history of correlation matrices:
    how average correlation changes over time.

    Provides stability, momentum, and trend metrics.
    """

    def __init__(self, window: int = 30) -> None:
        self._window = window
        self._avg_corr_history:  deque = deque(maxlen=window)
        self._abs_corr_history:  deque = deque(maxlen=window)
        self._n_pairs_history:   deque = deque(maxlen=window)

    def update(self, matrix: CorrelationMatrix) -> None:
        self._avg_corr_history.append(matrix.avg_correlation())
        self._abs_corr_history.append(matrix.avg_abs_correlation())
        self._n_pairs_history.append(matrix.n_pairs())

    # ── Queries ───────────────────────────────────────────────────────────

    def correlation_stability(self) -> float:
        """
        0-1 stability score.  1 = very stable (low std of avg correlation).
        Based on coefficient of variation of avg_correlation over time.
        """
        if len(self._avg_corr_history) < 3:
            return 0.5
        arr = np.array(self._avg_corr_history)
        std = float(np.std(arr))
        mean = float(np.mean(np.abs(arr)))
        if mean < 1e-9:
            return 0.5
        cv = std / (mean + 1e-9)
        return max(0.0, min(1.0, 1.0 - cv))

    def correlation_momentum(self) -> float:
        """
        Rate of change of average correlation.  Positive = rising correlation.
        Returns value roughly in [-1, 1].
        """
        if len(self._avg_corr_history) < 4:
            return 0.0
        arr = np.array(self._avg_corr_history)
        half = max(1, len(arr) // 2)
        recent = float(np.mean(arr[-half:]))
        older  = float(np.mean(arr[:half]))
        return max(-1.0, min(1.0, (recent - older) / (abs(older) + 1e-9)))

    def avg_rolling_correlation(self) -> float:
        if not self._avg_corr_history:
            return 0.0
        return float(np.mean(self._avg_corr_history))

    def avg_abs_rolling_correlation(self) -> float:
        if not self._abs_corr_history:
            return 0.0
        return float(np.mean(self._abs_corr_history))

    def is_rising(self) -> bool:
        return self.correlation_momentum() > 0.05

    def is_falling(self) -> bool:
        return self.correlation_momentum() < -0.05

    def __len__(self) -> int:
        return len(self._avg_corr_history)
