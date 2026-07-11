"""iios/investment/market/sector_rotation/sector_tracker.py
Stateful per-sector return history tracker.
"""
from __future__ import annotations

from collections import deque
from typing import Optional

from iios.investment.market.sector_rotation.models import (
    MarketSnapshot,
    SectorPerformance,
)
from iios.investment.market.sector_rotation.sector_performance import (
    compute_sector_performance,
    _weighted_avg_return,
)
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy


class SectorTracker:
    """Maintains a rolling return history for a single sector and computes
    :class:`SectorPerformance` on each update."""

    def __init__(self, sector: str, taxonomy: SectorTaxonomy, window: int = 120) -> None:
        self._sector   = sector
        self._taxonomy = taxonomy
        self._window   = window
        self._returns: deque[float] = deque(maxlen=window)
        self._current: Optional[SectorPerformance] = None

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def sector(self) -> str:
        return self._sector

    @property
    def current(self) -> Optional[SectorPerformance]:
        return self._current

    @property
    def history_length(self) -> int:
        return len(self._returns)

    def update(
        self,
        snapshot: MarketSnapshot,
    ) -> SectorPerformance:
        """Process one bar; return updated :class:`SectorPerformance`."""
        by_sector  = snapshot.by_sector()
        securities = by_sector.get(self._sector, [])

        # 1-bar return for this bar
        r1 = _weighted_avg_return(securities) if securities else 0.0
        self._returns.append(r1)

        perf = compute_sector_performance(
            sector=self._sector,
            securities=securities,
            benchmark_return=snapshot.benchmark_return,
            bar_index=snapshot.bar_index,
            return_history=self._returns,
            taxonomy=self._taxonomy,
        )
        self._current = perf
        return perf

    def peek_return_history(self, n: int) -> list:
        """Return last n single-bar returns (newest last)."""
        return list(self._returns)[-n:]
