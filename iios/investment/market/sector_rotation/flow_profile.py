"""iios/investment/market/sector_rotation/flow_profile.py
Builds CapitalFlowProfile from current security observations.
"""
from __future__ import annotations

from typing import List

from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    FlowType,
    SecurityData,
)
from iios.investment.market.sector_rotation.sector_performance import _breadth

_ACCUM_VOL_THR  = 1.4   # volume ratio threshold → accumulation
_DISTRIB_VOL_THR = 1.4
_NEUTRAL_BAND   = 0.3   # breadth must deviate this much from 0.5 for signal


def _classify_flow(breadth: float, volume_ratio: float) -> FlowType:
    up_side   = breadth >= (0.5 + _NEUTRAL_BAND)
    down_side = breadth <= (0.5 - _NEUTRAL_BAND)
    high_vol  = volume_ratio >= _ACCUM_VOL_THR

    if up_side and high_vol:
        return FlowType.INSTITUTIONAL_BUYING
    if up_side:
        return FlowType.ACCUMULATION
    if down_side and high_vol:
        return FlowType.INSTITUTIONAL_SELLING
    if down_side:
        return FlowType.DISTRIBUTION
    return FlowType.NEUTRAL


def _accumulation_score(breadth: float, volume_ratio: float) -> float:
    """0-100: 100 = maximum buying pressure."""
    vol_bonus = min(1.0, (volume_ratio - 1.0) / 1.0) * 20.0   # up to 20 pts
    return max(0.0, min(100.0, breadth * 80.0 + vol_bonus))


def _distribution_score(breadth: float, volume_ratio: float) -> float:
    """0-100: 100 = maximum selling pressure."""
    decline_breadth = 1.0 - breadth
    vol_bonus = min(1.0, (volume_ratio - 1.0) / 1.0) * 20.0
    return max(0.0, min(100.0, decline_breadth * 80.0 + vol_bonus))


def build_flow_profile(
    sector: str,
    securities: List[SecurityData],
    bar_index: int,
) -> CapitalFlowProfile:
    if not securities:
        return CapitalFlowProfile(
            sector=sector,
            bar_index=bar_index,
            flow_type=FlowType.NEUTRAL,
            flow_intensity=0.0,
            volume_ratio=1.0,
            accumulation_score=50.0,
            distribution_score=50.0,
            net_flow_signal=0.0,
        )

    breadth     = _breadth(securities)
    vol_ratios  = [s.volume_ratio for s in securities]
    vol_ratio   = sum(vol_ratios) / len(vol_ratios)

    flow_type   = _classify_flow(breadth, vol_ratio)
    accum_score = _accumulation_score(breadth, vol_ratio)
    distr_score = _distribution_score(breadth, vol_ratio)

    net_signal  = (accum_score - distr_score) / 100.0  # -1 to 1
    intensity   = abs(net_signal)

    return CapitalFlowProfile(
        sector=sector,
        bar_index=bar_index,
        flow_type=flow_type,
        flow_intensity=intensity,
        volume_ratio=vol_ratio,
        accumulation_score=accum_score,
        distribution_score=distr_score,
        net_flow_signal=net_signal,
    )
