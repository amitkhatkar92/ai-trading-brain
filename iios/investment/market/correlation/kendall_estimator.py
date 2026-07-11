"""iios/investment/market/correlation/kendall_estimator.py
Kendall tau-b rank correlation estimator.
"""
from __future__ import annotations

import numpy as np

from iios.investment.market.correlation.models import CorrelationMethod


def _kendall_tau_b(x: np.ndarray, y: np.ndarray) -> float:
    """
    Kendall tau-b, O(n²) implementation.
    Handles ties in both x and y via the tau-b formula.
    """
    n = len(x)
    concordant = discordant = 0
    ties_x = ties_y = 0

    for i in range(n - 1):
        for j in range(i + 1, n):
            dx = x[j] - x[i]
            dy = y[j] - y[i]
            sx = int(dx > 0) - int(dx < 0)
            sy = int(dy > 0) - int(dy < 0)
            if sx == 0:
                ties_x += 1
            if sy == 0:
                ties_y += 1
            product = sx * sy
            if product > 0:
                concordant += 1
            elif product < 0:
                discordant += 1

    total_pairs = n * (n - 1) // 2
    n0 = total_pairs
    denom = ((n0 - ties_x) * (n0 - ties_y)) ** 0.5
    if denom == 0:
        return 0.0
    return (concordant - discordant) / denom


class KendallEstimator:
    """Kendall tau-b correlation estimator."""

    @property
    def name(self) -> str:
        return "kendall"

    @property
    def method(self) -> CorrelationMethod:
        return CorrelationMethod.KENDALL

    @property
    def min_observations(self) -> int:
        return 4

    def estimate(self, x: np.ndarray, y: np.ndarray) -> float:
        n = len(x)
        if n < self.min_observations or len(y) != n:
            return 0.0
        try:
            r = _kendall_tau_b(x.astype(float), y.astype(float))
            if np.isnan(r) or np.isinf(r):
                return 0.0
            return max(-1.0, min(1.0, r))
        except Exception:
            return 0.0
