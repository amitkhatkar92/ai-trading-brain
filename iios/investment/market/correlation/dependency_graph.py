"""iios/investment/market/correlation/dependency_graph.py
DependencyGraph builder from lead-lag cross-correlation analysis.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from iios.investment.market.correlation.models import (
    DependencyEdge,
    DependencyGraph,
    DependencyType,
)
from iios.investment.market.correlation.pearson_estimator import PearsonEstimator


_pearson = PearsonEstimator()


def _cross_correlation_at_lag(
    x: np.ndarray,   # potential leader (older values)
    y: np.ndarray,   # potential follower (current values)
    lag: int,
    window: int,
) -> float:
    """
    Compute correlation between x[t-lag] and y[t].
    A positive result at lag > 0 means x leads y.
    """
    if len(x) < window + lag or len(y) < window:
        return 0.0
    x_slice = x[-(window + lag):-lag] if lag > 0 else x[-window:]
    y_slice = y[-window:]
    if len(x_slice) < 3 or len(x_slice) != len(y_slice):
        return 0.0
    return _pearson.estimate(x_slice, y_slice)


def build_dependency_graph(
    symbol_returns: Dict[str, np.ndarray],
    window: int,
    max_lag: int = 5,
    min_corr: float = 0.30,
    confidence_threshold: float = 0.20,
    bar_index: int = 0,
    timestamp: float = 0.0,
) -> DependencyGraph:
    """
    Build a directed DependencyGraph from lead-lag cross-correlations.

    For each ordered pair (A, B), compute cross-correlation at lags 1..max_lag.
    If the cross-correlation at lag k is significantly higher than the
    contemporaneous correlation, A leads B by k bars.
    """
    symbols = [s for s, arr in symbol_returns.items()
               if len(arr) >= window + max_lag]

    if len(symbols) < 2:
        return DependencyGraph(edges=[], bar_index=bar_index, timestamp=timestamp)

    # Contemporaneous correlations
    contemp: Dict[Tuple[str, str], float] = {}
    for i, sa in enumerate(symbols):
        for sb in symbols[i + 1:]:
            xa = symbol_returns[sa][-window:]
            xb = symbol_returns[sb][-window:]
            if len(xa) == len(xb) >= 3:
                r = _pearson.estimate(xa, xb)
                contemp[(sa, sb)] = r
                contemp[(sb, sa)] = r

    edges: List[DependencyEdge] = []

    for sa in symbols:
        for sb in symbols:
            if sa == sb:
                continue
            xa = symbol_returns[sa]
            xb = symbol_returns[sb]
            best_lag_corr = 0.0
            best_lag      = 0

            for lag in range(1, max_lag + 1):
                lag_corr = _cross_correlation_at_lag(xa, xb, lag, window)
                if abs(lag_corr) > abs(best_lag_corr):
                    best_lag_corr = lag_corr
                    best_lag      = lag

            if abs(best_lag_corr) < min_corr:
                continue

            # Only flag as leading if lag correlation is materially stronger
            c0 = contemp.get((sa, sb), 0.0)
            if abs(best_lag_corr) <= abs(c0) + confidence_threshold:
                continue

            confidence = min(1.0, (abs(best_lag_corr) - abs(c0)) / 0.50)
            edges.append(DependencyEdge(
                source=sa,
                target=sb,
                lag_bars=best_lag,
                correlation=best_lag_corr,
                dependency_type=DependencyType.LEADING,
                confidence=confidence,
            ))

    return DependencyGraph(
        edges=edges,
        bar_index=bar_index,
        timestamp=timestamp,
    )
