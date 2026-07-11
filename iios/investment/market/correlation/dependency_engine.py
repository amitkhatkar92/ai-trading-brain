"""iios/investment/market/correlation/dependency_engine.py
Stateful dependency analysis engine: builds and caches the dependency
graph from rolling return histories.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional

import numpy as np

from iios.investment.market.correlation.models import (
    CorrelationMatrix,
    DependencyGraph,
    MultiAssetSnapshot,
)
from iios.investment.market.correlation.dependency_graph import build_dependency_graph
from iios.investment.market.correlation.rolling_correlation import RollingCorrelationCalculator


class DependencyEngine:
    """
    Maintains extended-length return histories for lead-lag analysis and
    produces a DependencyGraph on each update.

    Uses longer history than the primary rolling window to allow lag
    calculation at lags 1..max_lag.
    """

    def __init__(
        self,
        primary_calc: RollingCorrelationCalculator,
        window: int = 60,
        max_lag: int = 5,
        min_corr: float = 0.30,
        history_size: int = 50,
    ) -> None:
        self._primary_calc = primary_calc
        self._window       = window
        self._max_lag      = max_lag
        self._min_corr     = min_corr

        # Extended histories: window + max_lag to support cross-correlation
        self._ext_window   = window + max_lag
        self._histories: Dict[str, deque] = {}

        self._graph_history: deque = deque(maxlen=history_size)
        self._current: Optional[DependencyGraph] = None

    def update(
        self,
        snapshot: MultiAssetSnapshot,
        matrix: Optional[CorrelationMatrix],
    ) -> DependencyGraph:
        """Update extended histories and recompute the dependency graph."""
        for obs in snapshot.observations:
            if obs.symbol not in self._histories:
                self._histories[obs.symbol] = deque(maxlen=self._ext_window)
            if obs.return_pct is not None:
                self._histories[obs.symbol].append(obs.return_pct)

        # Build graph only when enough history
        min_hist = min(
            (len(h) for h in self._histories.values()),
            default=0
        )
        if min_hist < self._window + self._max_lag or len(self._histories) < 2:
            graph = DependencyGraph(
                edges=[],
                bar_index=snapshot.bar_index,
                timestamp=snapshot.timestamp,
            )
        else:
            arrays = {
                s: np.array(list(h))
                for s, h in self._histories.items()
            }
            graph = build_dependency_graph(
                symbol_returns=arrays,
                window=self._window,
                max_lag=self._max_lag,
                min_corr=self._min_corr,
                bar_index=snapshot.bar_index,
                timestamp=snapshot.timestamp,
            )

        self._graph_history.append(graph)
        self._current = graph
        return graph

    @property
    def current(self) -> Optional[DependencyGraph]:
        return self._current

    def recent(self, n: int = 10) -> List[DependencyGraph]:
        return list(self._graph_history)[-n:]
