"""iios/investment/market/breadth/breadth_statistics.py
Rolling statistics over a stream of breadth_pct and ad_ratio values.
"""
from __future__ import annotations

import bisect
import math
from collections import deque
from typing import Deque, List, Tuple

from iios.investment.market.breadth.models import BreadthTrend


class BreadthStatistics:
    """Rolling window statistics for market breadth metrics."""

    def __init__(self, window: int = 50) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        self._window = window
        self._breadth_pct: Deque[float] = deque(maxlen=window)
        self._ad_ratio: Deque[float] = deque(maxlen=window)
        self._above_ma20: Deque[float] = deque(maxlen=window)
        self._health_score: Deque[float] = deque(maxlen=window)

    # ── Mutation ──────────────────────────────────────────────────────────

    def update(
        self,
        breadth_pct: float,
        ad_ratio: float,
        above_ma20_pct: float,
        health_score: float,
    ) -> None:
        self._breadth_pct.append(breadth_pct)
        self._ad_ratio.append(ad_ratio)
        self._above_ma20.append(above_ma20_pct)
        self._health_score.append(health_score)

    # ── Queries ───────────────────────────────────────────────────────────

    @property
    def count(self) -> int:
        return len(self._breadth_pct)

    def breadth_trend(self, short: int = 5, long: int = 20) -> BreadthTrend:
        vals = list(self._breadth_pct)
        n = len(vals)
        if n < 3:
            return BreadthTrend.STABLE
        short_avg = sum(vals[-min(short, n):]) / min(short, n)
        long_avg  = sum(vals[-min(long, n):]) / min(long, n)
        delta = short_avg - long_avg
        if delta > 0.15:
            return BreadthTrend.SURGING
        if delta > 0.05:
            return BreadthTrend.RISING
        if delta < -0.15:
            return BreadthTrend.COLLAPSING
        if delta < -0.05:
            return BreadthTrend.FALLING
        return BreadthTrend.STABLE

    def breadth_momentum(self, short: int = 3, long: int = 10) -> float:
        """Rate of change of breadth_pct (-1 to 1)."""
        vals = list(self._breadth_pct)
        n = len(vals)
        if n < 2:
            return 0.0
        recent   = sum(vals[-min(short, n):]) / min(short, n)
        baseline = sum(vals[-min(long, n):]) / min(long, n)
        if baseline < 1e-10:
            return 0.0
        return max(-1.0, min(1.0, (recent - baseline) / baseline))

    def breadth_stability(self) -> float:
        """Inverse of normalised std dev of breadth_pct (0-1)."""
        vals = list(self._breadth_pct)
        n = len(vals)
        if n < 2:
            return 0.5
        mu  = sum(vals) / n
        std = math.sqrt(sum((v - mu) ** 2 for v in vals) / (n - 1))
        return 1.0 / (1.0 + std / max(mu, 1e-8))

    def health_momentum(self) -> float:
        """Rate of change of health score (-1 to 1)."""
        vals = list(self._health_score)
        n = len(vals)
        if n < 3:
            return 0.0
        recent   = vals[-1]
        baseline = sum(vals[-min(5, n):]) / min(5, n)
        return max(-1.0, min(1.0, (recent - baseline) / max(baseline, 1.0)))

    def avg_breadth_pct(self, n: int = 20) -> float:
        vals = list(self._breadth_pct)
        sample = vals[-min(n, len(vals)):]
        return sum(sample) / len(sample) if sample else 0.5

    def avg_above_ma20(self, n: int = 20) -> float:
        vals = list(self._above_ma20)
        sample = vals[-min(n, len(vals)):]
        return sum(sample) / len(sample) if sample else 0.5
