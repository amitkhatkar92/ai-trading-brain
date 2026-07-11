"""iios/investment/market/sector_rotation/sector_snapshot.py
Builds a dict[sector -> SectorPerformance] for a given MarketSnapshot.
"""
from __future__ import annotations

from typing import Dict, List

from iios.investment.market.sector_rotation.models import (
    MarketSnapshot,
    SectorPerformance,
)
from iios.investment.market.sector_rotation.sector_tracker import SectorTracker
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy


class SectorSnapshotBuilder:
    """Manages a pool of :class:`SectorTracker` instances and produces a
    complete sector-performance map on each bar."""

    def __init__(self, taxonomy: SectorTaxonomy, window: int = 120) -> None:
        self._taxonomy  = taxonomy
        self._window    = window
        self._trackers: Dict[str, SectorTracker] = {}

    def _get_tracker(self, sector: str) -> SectorTracker:
        if sector not in self._trackers:
            self._trackers[sector] = SectorTracker(sector, self._taxonomy, self._window)
        return self._trackers[sector]

    def update(self, snapshot: MarketSnapshot) -> Dict[str, SectorPerformance]:
        """Update all sector trackers; return current performance for all sectors."""
        present: List[str] = snapshot.sectors()

        # Ensure known taxonomy sectors are always tracked even if empty
        for s in self._taxonomy.sectors():
            if s not in present:
                self._get_tracker(s)   # initialise but don't update (no data)

        result: Dict[str, SectorPerformance] = {}
        for sector in present:
            tracker = self._get_tracker(sector)
            result[sector] = tracker.update(snapshot)

        return result

    @property
    def active_sectors(self) -> List[str]:
        return sorted(self._trackers.keys())
