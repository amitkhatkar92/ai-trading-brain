"""iios/investment/market/sector_rotation/industry_tracker.py
Stateful per-industry return history tracker.
"""
from __future__ import annotations

from collections import deque
from typing import List, Optional

from iios.investment.market.sector_rotation.models import (
    IndustryProfile,
    MarketSnapshot,
    SecurityData,
)
from iios.investment.market.sector_rotation.sector_performance import (
    _breadth,
    _rolling_return,
    _weighted_avg_return,
)

_MOMENTUM_W = (0.5, 0.3, 0.2)   # weights for 1/5/20-bar relative returns


def _ind_momentum(r1: float, r5: float, r20: float) -> float:
    weighted = _MOMENTUM_W[0] * r1 + _MOMENTUM_W[1] * r5 + _MOMENTUM_W[2] * r20
    clipped  = max(-0.10, min(0.10, weighted))
    return 50.0 + clipped * 500.0


class IndustryTracker:
    """Maintains rolling history for one industry and produces
    :class:`IndustryProfile` on each update."""

    def __init__(self, industry: str, parent_sector: str, window: int = 120) -> None:
        self._industry = industry
        self._sector   = parent_sector
        self._window   = window
        self._returns: deque[float] = deque(maxlen=window)
        self._current: Optional[IndustryProfile] = None

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def industry(self) -> str:
        return self._industry

    @property
    def sector(self) -> str:
        return self._sector

    @property
    def current(self) -> Optional[IndustryProfile]:
        return self._current

    def update(
        self,
        securities: List[SecurityData],
        benchmark_return: float,
        sector_return_1bar: float,
        bar_index: int,
    ) -> IndustryProfile:
        r1 = _weighted_avg_return(securities) if securities else 0.0
        self._returns.append(r1)

        r5  = _rolling_return(self._returns, 5)
        r20 = _rolling_return(self._returns, 20)

        rel_sector    = r1 - sector_return_1bar
        rel_benchmark = r1 - benchmark_return
        mom_score     = _ind_momentum(rel_sector, r5 - sector_return_1bar * 5, r20 - sector_return_1bar * 20)
        breadth       = _breadth(securities)

        profile = IndustryProfile(
            industry=self._industry,
            sector=self._sector,
            bar_index=bar_index,
            return_1bar=r1,
            return_5bar=r5,
            return_20bar=r20,
            rel_to_sector=rel_sector,
            rel_to_benchmark=rel_benchmark,
            momentum_score=mom_score,
            breadth_pct=breadth,
            n_securities=len(securities),
        )
        self._current = profile
        return profile
