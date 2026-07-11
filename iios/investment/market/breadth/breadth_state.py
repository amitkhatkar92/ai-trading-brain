"""iios/investment/market/breadth/breadth_state.py
Stateful tracker: accumulates A/D line and rolling breadth statistics.
"""
from __future__ import annotations

from iios.investment.market.breadth.breadth_statistics import BreadthStatistics
from iios.investment.market.breadth.models import BreadthData, BreadthTrend


class BreadthStateTracker:
    """
    Maintains the cumulative A/D line and rolling breadth statistics.

    Parameters
    ----------
    window: rolling window size for statistics
    """

    def __init__(self, window: int = 50) -> None:
        self._window = window
        self._ad_line: float = 0.0
        self._bars_processed: int = 0
        self._stats = BreadthStatistics(window=window)

    # ── Public API ─────────────────────────────────────────────────────────

    def update(
        self,
        advancing: int,
        declining: int,
        unchanged: int,
        total: int,
        above_ma20_pct: float,
        health_score: float,
        metric_values: dict,
    ) -> BreadthData:
        """
        Consume raw counts from the latest universe snapshot and return
        an updated BreadthData.
        """
        self._bars_processed += 1
        self._ad_line += advancing - declining

        breadth_pct = advancing / max(total, 1)
        ad_ratio    = advancing / max(declining, 1)

        self._stats.update(breadth_pct, ad_ratio, above_ma20_pct, health_score)

        momentum  = self._stats.breadth_momentum()
        trend     = self._stats.breadth_trend()
        stability = self._stats.breadth_stability()

        return BreadthData(
            advancing=advancing,
            declining=declining,
            unchanged=unchanged,
            total=total,
            breadth_pct=breadth_pct,
            ad_ratio=ad_ratio,
            ad_line=self._ad_line,
            ad_momentum=momentum,
            breadth_trend=trend,
            breadth_stability=stability,
            metric_values=metric_values,
        )

    @property
    def ad_line(self) -> float:
        return self._ad_line

    @property
    def bars_processed(self) -> int:
        return self._bars_processed

    @property
    def statistics(self) -> BreadthStatistics:
        return self._stats
