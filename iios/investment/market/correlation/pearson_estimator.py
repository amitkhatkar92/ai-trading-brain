"""iios/investment/market/correlation/pearson_estimator.py
Pearson product-moment correlation estimator.
"""
from __future__ import annotations

import numpy as np

from iios.investment.market.correlation.models import CorrelationMethod


class PearsonEstimator:
    """Standard Pearson r using numpy for efficiency."""

    @property
    def name(self) -> str:
        return "pearson"

    @property
    def method(self) -> CorrelationMethod:
        return CorrelationMethod.PEARSON

    @property
    def min_observations(self) -> int:
        return 3

    def estimate(self, x: np.ndarray, y: np.ndarray) -> float:
        n = len(x)
        if n < self.min_observations or len(y) != n:
            return 0.0
        try:
            x = x.astype(float)
            y = y.astype(float)
            corr_matrix = np.corrcoef(x, y)
            r = float(corr_matrix[0, 1])
            if np.isnan(r) or np.isinf(r):
                return 0.0
            return max(-1.0, min(1.0, r))
        except Exception:
            return 0.0
