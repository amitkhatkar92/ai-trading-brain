"""iios/investment/market/sector_rotation/sector_score.py
Composite sector score combining RS, momentum, flow and lifecycle.
"""
from __future__ import annotations

from typing import Dict

from iios.investment.market.sector_rotation.models import (
    CapitalFlowProfile,
    RelativeStrengthScore,
    SectorLifecycleProfile,
    SectorPerformance,
    SectorStage,
)

# Lifecycle stage score boost/penalty
_STAGE_SCORE: Dict[SectorStage, float] = {
    SectorStage.LEADING:         20.0,
    SectorStage.OUTPERFORMING:   15.0,
    SectorStage.EMERGING:        10.0,
    SectorStage.MATURE:          0.0,
    SectorStage.RECOVERING:      5.0,
    SectorStage.WEAKENING:      -10.0,
    SectorStage.LAGGING:        -20.0,
    SectorStage.UNDERPERFORMING: -15.0,
    SectorStage.UNKNOWN:          0.0,
}


def compute_composite_score(
    perf: SectorPerformance,
    rs: RelativeStrengthScore,
    flow: CapitalFlowProfile,
    lifecycle: SectorLifecycleProfile,
) -> float:
    """Produce a 0-100 composite score for the sector.

    Weights:
    - Relative strength composite : 35%
    - Momentum score               : 30%
    - Capital flow (net signal)    : 20%  (mapped 0-100)
    - Lifecycle stage bonus        : 15%
    """
    rs_component       = rs.composite                             # 0-100
    momentum_component = perf.momentum_score                      # 0-100
    flow_component     = (flow.net_flow_signal + 1.0) * 50.0      # -1..1 → 0-100
    stage_raw          = _STAGE_SCORE.get(lifecycle.stage, 0.0)
    lifecycle_component = 50.0 + stage_raw                        # 30-70

    composite = (
        rs_component       * 0.35
        + momentum_component * 0.30
        + flow_component     * 0.20
        + lifecycle_component * 0.15
    )
    return max(0.0, min(100.0, composite))
