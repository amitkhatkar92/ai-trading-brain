"""iios/investment/market/volatility/volatility_statistics.py
Rolling statistics over a stream of annualised volatility values.

Provides mean, std, percentile rank (normalisation) and multi-window averages
used by the state tracker and downstream components.
"""
from __future__ import annotations

import bisect
import math
from collections import deque
from typing import Deque, List, Tuple


class VolatilityStatistics:
    """
    Maintains a rolling window of annualised volatility values and exposes
    descriptive statistics used to compute relative and normalised vol.
    """

    def __init__(self, window: int = 50) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        self._window = window
        self._values: Deque[float] = deque(maxlen=window)
        self._sorted: List[float] = []   # kept sorted for O(log n) percentile

    # ── Mutation ──────────────────────────────────────────────────────────

    def update(self, annualized_vol: float) -> None:
        """Add one annualised vol observation."""
        if len(self._values) == self._window:
            # Remove oldest from sorted list
            oldest = self._values[0]
            idx = bisect.bisect_left(self._sorted, oldest)
            if 0 <= idx < len(self._sorted) and self._sorted[idx] == oldest:
                self._sorted.pop(idx)

        self._values.append(annualized_vol)
        bisect.insort(self._sorted, annualized_vol)

    # ── Queries ───────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return len(self._values)

    @property
    def mean(self) -> float:
        if not self._values:
            return 0.0
        return sum(self._values) / len(self._values)

    @property
    def std(self) -> float:
        n = len(self._values)
        if n < 2:
            return 0.0
        mu = self.mean
        return math.sqrt(sum((v - mu) ** 2 for v in self._values) / (n - 1))

    @property
    def minimum(self) -> float:
        return self._sorted[0] if self._sorted else 0.0

    @property
    def maximum(self) -> float:
        return self._sorted[-1] if self._sorted else 0.0

    def window_mean(self, n: int) -> float:
        """Mean of the last *n* observations (or fewer if insufficient)."""
        if not self._values:
            return 0.0
        sample = list(self._values)[-n:]
        return sum(sample) / len(sample)

    def percentile_rank(self, value: float) -> float:
        """Return the percentile rank of *value* in (0, 1]."""
        if not self._sorted:
            return 0.5
        rank = bisect.bisect_right(self._sorted, value)
        return rank / len(self._sorted)

    def normalized(self, value: float) -> float:
        """Percentile rank clamped to [0, 1]."""
        return max(0.0, min(1.0, self.percentile_rank(value)))

    def multi_window_means(
        self, short: int = 5, medium: int = 20, long: int = 50
    ) -> Tuple[float, float, float]:
        """Return (short_mean, medium_mean, long_mean)."""
        return (
            self.window_mean(short),
            self.window_mean(medium),
            self.window_mean(long),
        )

    def lag1_autocorrelation(self) -> float:
        """
        Lag-1 autocorrelation of the stored series as a proxy for volatility
        clustering / persistence.  Result clamped to [0, 1].
        """
        vals = list(self._values)
        n = len(vals)
        if n < 4:
            return 0.5
        mu = sum(vals) / n
        cov = sum((vals[i] - mu) * (vals[i - 1] - mu) for i in range(1, n))
        var = sum((v - mu) ** 2 for v in vals)
        if var == 0.0:
            return 0.5
        autocorr = cov / var
        return max(0.0, min(1.0, (autocorr + 1.0) / 2.0))
