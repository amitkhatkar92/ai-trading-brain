"""iios/investment/market/sector_rotation/capital_flow_engine.py
Orchestrates capital flow tracking across all sectors.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from iios.investment.market.sector_rotation.flow_statistics import (
    cyclical_sectors_buying,
    defensive_sectors_buying,
    flow_dispersion,
    top_inflow_sectors,
    top_outflow_sectors,
)
from iios.investment.market.sector_rotation.flow_tracker import FlowTracker
from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    FlowType,
    MarketSnapshot,
)
from iios.investment.market.sector_rotation.sector_taxonomy import SectorTaxonomy

log = logging.getLogger(__name__)


class CapitalFlowEngine:
    """Maintains FlowTracker instances for every sector and provides
    aggregated capital-flow intelligence."""

    def __init__(self, taxonomy: SectorTaxonomy, window: int = 60) -> None:
        self._taxonomy  = taxonomy
        self._window    = window
        self._trackers: Dict[str, FlowTracker] = {}
        self._current:  Dict[str, CapitalFlowProfile] = {}

    # ── update ────────────────────────────────────────────────────────────────

    def update(self, snapshot: MarketSnapshot) -> Dict[str, CapitalFlowProfile]:
        by_sector = snapshot.by_sector()
        result: Dict[str, CapitalFlowProfile] = {}

        for sector, securities in by_sector.items():
            if sector not in self._trackers:
                self._trackers[sector] = FlowTracker(sector, self._window)
            profile = self._trackers[sector].update(securities, snapshot.bar_index)
            result[sector] = profile

        self._current = result
        return result

    # ── queries ───────────────────────────────────────────────────────────────

    def current_flows(self) -> Dict[str, CapitalFlowProfile]:
        return dict(self._current)

    def get(self, sector: str) -> Optional[CapitalFlowProfile]:
        return self._current.get(sector)

    def inflow_sectors(self, n: int = 3) -> List[str]:
        return top_inflow_sectors(self._current, n)

    def outflow_sectors(self, n: int = 3) -> List[str]:
        return top_outflow_sectors(self._current, n)

    def defensive_flow(self, lookback: int = 5) -> float:
        return defensive_sectors_buying(
            self._trackers,
            self._taxonomy.defensive_sectors(),
            lookback,
        )

    def cyclical_flow(self, lookback: int = 5) -> float:
        return cyclical_sectors_buying(
            self._trackers,
            self._taxonomy.cyclical_sectors(),
            lookback,
        )

    def dispersion(self) -> float:
        return flow_dispersion(self._current)

    def is_defensive_rotation(self, lookback: int = 5) -> bool:
        """Returns True when capital is moving into defensives and out of cyclicals."""
        return (
            self.defensive_flow(lookback) > 0.1
            and self.cyclical_flow(lookback) < -0.1
        )

    def is_risk_on_rotation(self, lookback: int = 5) -> bool:
        return (
            self.cyclical_flow(lookback) > 0.1
            and self.defensive_flow(lookback) < -0.1
        )
