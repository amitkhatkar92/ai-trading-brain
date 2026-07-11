"""iios/investment/market/correlation/spearman_estimator.py
Spearman rank correlation estimator.
Computes Pearson r on rank-transformed data for robustness to outliers.
"""
from __future__ import annotations

import numpy as np

from iios.investment.market.correlation.models import CorrelationMethod


def _rank(x: np.ndarray) -> np.ndarray:
    """Convert values to ranks with average-rank tie handling."""
    n = len(x)
    idx = np.argsort(x, kind="stable")
    ranks = np.empty(n, dtype=float)
    ranks[idx] = np.arange(1, n + 1, dtype=float)
    # Tie handling: average ranks for equal values
    i = 0
    while i < n:
        j = i
        while j < n - 1 and x[idx[j]] == x[idx[j + 1]]:
            j += 1
        if j > i:
            avg = (i + j + 2) / 2.0
            for k in range(i, j + 1):
                ranks[idx[k]] = avg
        i = j + 1
    return ranks


class SpearmanEstimator:
    """Spearman rank correlation via rank-transform + Pearson."""

    @property
    def name(self) -> str:
        return "spearman"

    @property
    def method(self) -> CorrelationMethod:
        return CorrelationMethod.SPEARMAN

    @property
    def min_observations(self) -> int:
        return 3

    def estimate(self, x: np.ndarray, y: np.ndarray) -> float:
        n = len(x)
        if n < self.min_observations or len(y) != n:
            return 0.0
        try:
            rx = _rank(x.astype(float))
            ry = _rank(y.astype(float))
            corr_matrix = np.corrcoef(rx, ry)
            r = float(corr_matrix[0, 1])
            if np.isnan(r) or np.isinf(r):
                return 0.0
            return max(-1.0, min(1.0, r))
        except Exception:
            return 0.0
