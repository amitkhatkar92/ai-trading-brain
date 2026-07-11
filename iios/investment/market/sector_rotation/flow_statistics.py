"""iios/investment/market/sector_rotation/flow_statistics.py
Rolling capital-flow statistics across all tracked sectors.
"""
from __future__ import annotations

from typing import Dict, List

from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    FlowType,
)
from iios.investment.market.sector_rotation.flow_tracker import FlowTracker


def defensive_sectors_buying(
    trackers: Dict[str, FlowTracker],
    defensive_sectors: List[str],
    lookback: int = 5,
) -> float:
    """Average net_flow_signal across defensive sectors over last n bars."""
    signals = [
        trackers[s].rolling_net_signal(lookback)
        for s in defensive_sectors
        if s in trackers
    ]
    if not signals:
        return 0.0
    return sum(signals) / len(signals)


def cyclical_sectors_buying(
    trackers: Dict[str, FlowTracker],
    cyclical_sectors: List[str],
    lookback: int = 5,
) -> float:
    signals = [
        trackers[s].rolling_net_signal(lookback)
        for s in cyclical_sectors
        if s in trackers
    ]
    if not signals:
        return 0.0
    return sum(signals) / len(signals)


def top_inflow_sectors(
    current_flows: Dict[str, CapitalFlowProfile],
    n: int = 3,
) -> List[str]:
    """Sectors with highest net_flow_signal."""
    ranked = sorted(
        current_flows.values(),
        key=lambda f: f.net_flow_signal,
        reverse=True,
    )
    return [f.sector for f in ranked[:n]]


def top_outflow_sectors(
    current_flows: Dict[str, CapitalFlowProfile],
    n: int = 3,
) -> List[str]:
    ranked = sorted(
        current_flows.values(),
        key=lambda f: f.net_flow_signal,
    )
    return [f.sector for f in ranked[:n]]


def flow_dispersion(current_flows: Dict[str, CapitalFlowProfile]) -> float:
    """Standard deviation of net_flow_signal across sectors (0 = uniform)."""
    if len(current_flows) < 2:
        return 0.0
    signals = [f.net_flow_signal for f in current_flows.values()]
    mean    = sum(signals) / len(signals)
    var     = sum((x - mean) ** 2 for x in signals) / len(signals)
    return var ** 0.5
