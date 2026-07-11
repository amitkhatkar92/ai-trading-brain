"""iios/investment/market/correlation/correlation_estimator.py
Pluggable correlation estimator Protocol.

Any class satisfying CorrelationEstimator can be registered with the engine
without modifying core logic.  Built-in implementations: Pearson, Spearman,
Kendall.
"""
from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

import numpy as np

from iios.investment.market.correlation.models import CorrelationMethod


@runtime_checkable
class CorrelationEstimator(Protocol):
    """Structural protocol for stateless pairwise correlation estimators."""

    @property
    def name(self) -> str:
        """Unique name used as registry key."""
        ...

    @property
    def method(self) -> CorrelationMethod:
        """Correlation method enum value."""
        ...

    @property
    def min_observations(self) -> int:
        """Minimum number of observations required for a valid estimate."""
        ...

    def estimate(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Compute the correlation coefficient between x and y.

        Parameters
        ----------
        x, y : 1-D numpy arrays of equal length containing return observations.

        Returns
        -------
        float in [-1, 1].  Returns 0.0 if insufficient observations or
        computation fails.
        """
        ...
