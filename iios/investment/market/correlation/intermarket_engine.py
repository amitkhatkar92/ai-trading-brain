"""iios/investment/market/correlation/intermarket_engine.py
Stateful intermarket intelligence orchestrator.
"""
from __future__ import annotations

from collections import deque
from typing import List, Optional

from iios.investment.market.correlation.models import (
    CorrelationMatrix,
    IntermarketAnalysis,
    MultiAssetSnapshot,
)
from iios.investment.market.correlation.cross_asset_analysis import CrossAssetAnalyzer


class IntermarketEngine:
    """
    Wraps CrossAssetAnalyzer with stateful history tracking.
    Keeps a rolling cache of past IntermarketAnalysis objects.
    """

    def __init__(self, history_size: int = 100) -> None:
        self._analyzer = CrossAssetAnalyzer()
        self._history: deque = deque(maxlen=history_size)
        self._current: Optional[IntermarketAnalysis] = None

    def update(
        self,
        matrix: CorrelationMatrix,
        snapshot: MultiAssetSnapshot,
    ) -> IntermarketAnalysis:
        analysis = self._analyzer.analyze(matrix, snapshot)
        self._history.append(analysis)
        self._current = analysis
        return analysis

    @property
    def current(self) -> Optional[IntermarketAnalysis]:
        return self._current

    def recent(self, n: int = 10) -> List[IntermarketAnalysis]:
        return list(self._history)[-n:]

    def persistent_anomaly_count(self, lookback: int = 5) -> int:
        """Count anomalies that have persisted for at least `lookback` bars."""
        recent = self.recent(lookback)
        if len(recent) < lookback:
            return 0
        first_set = {
            (r.asset_class_a, r.asset_class_b)
            for r in recent[0].anomalies
        }
        for analysis in recent[1:]:
            current_set = {
                (r.asset_class_a, r.asset_class_b)
                for r in analysis.anomalies
            }
            first_set &= current_set
        return len(first_set)

    def history_length(self) -> int:
        return len(self._history)
