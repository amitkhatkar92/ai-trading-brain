"""iios/investment/market/correlation/correlation_matrix.py
CorrelationMatrix construction helpers.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from iios.investment.market.correlation.models import (
    CorrelationMatrix,
    CorrelationMethod,
)
from iios.investment.market.correlation.correlation_estimator import CorrelationEstimator


def build_correlation_matrix(
    symbols: List[str],
    return_arrays: Dict[str, np.ndarray],
    estimator: CorrelationEstimator,
    window: int,
    bar_index: int,
    timestamp: float,
) -> CorrelationMatrix:
    """
    Build a full N×N CorrelationMatrix from a dict of return arrays.

    Parameters
    ----------
    symbols       : ordered list of symbols to include
    return_arrays : symbol → 1-D numpy array of recent returns
    estimator     : pluggable correlation estimator
    window        : rolling window size
    bar_index     : current bar index
    timestamp     : current timestamp
    """
    valid = [s for s in symbols if s in return_arrays
             and len(return_arrays[s]) >= estimator.min_observations]

    n_obs = min(len(return_arrays[s]) for s in valid) if valid else 0

    if len(valid) >= 2 and estimator.method == CorrelationMethod.PEARSON:
        data = _build_pearson_numpy(valid, return_arrays, n_obs)
    else:
        data = _build_pairwise(valid, return_arrays, estimator)

    confidence = min(1.0, n_obs / max(window, 1))

    return CorrelationMatrix(
        symbols=valid,
        data=data,
        method=estimator.method,
        window=window,
        n_observations=n_obs,
        bar_index=bar_index,
        timestamp=timestamp,
        confidence=confidence,
    )


def _build_pearson_numpy(
    symbols: List[str],
    arrays: Dict[str, np.ndarray],
    n_obs: int,
) -> Dict[str, Dict[str, float]]:
    """Efficient batch Pearson using np.corrcoef."""
    mat = np.array([arrays[s][-n_obs:] for s in symbols], dtype=float)
    with np.errstate(invalid='ignore', divide='ignore'):
        corr = np.corrcoef(mat)
    corr = np.where(np.isnan(corr) | np.isinf(corr), 0.0, corr)
    corr = np.clip(corr, -1.0, 1.0)

    data: Dict[str, Dict[str, float]] = {}
    for i, si in enumerate(symbols):
        data[si] = {}
        for j, sj in enumerate(symbols):
            data[si][sj] = float(corr[i, j])
    return data


def _build_pairwise(
    symbols: List[str],
    arrays: Dict[str, np.ndarray],
    estimator: CorrelationEstimator,
) -> Dict[str, Dict[str, float]]:
    """Pairwise correlation for non-Pearson estimators."""
    data: Dict[str, Dict[str, float]] = {s: {s: 1.0} for s in symbols}
    for i, si in enumerate(symbols):
        for sj in symbols[i + 1:]:
            xi = arrays[si]
            xj = arrays[sj]
            n = min(len(xi), len(xj))
            r = estimator.estimate(xi[-n:], xj[-n:])
            data[si][sj] = r
            data[sj][si] = r
    return data


def empty_correlation_matrix(bar_index: int, timestamp: float) -> CorrelationMatrix:
    return CorrelationMatrix(
        symbols=[],
        data={},
        method=CorrelationMethod.PEARSON,
        window=0,
        n_observations=0,
        bar_index=bar_index,
        timestamp=timestamp,
        confidence=0.0,
    )
