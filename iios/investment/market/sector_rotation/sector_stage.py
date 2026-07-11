"""iios/investment/market/sector_rotation/sector_stage.py
Rules-based lifecycle stage classification for a single sector.
"""
from __future__ import annotations

from iios.investment.market.sector_rotation.models import (
    RelativeStrengthScore,
    SectorPerformance,
    SectorStage,
)

_RS_LEADING_THR   = 60.0   # composite RS score
_RS_LAGGING_THR   = 40.0
_MOM_STRONG_THR   = 58.0
_MOM_WEAK_THR     = 42.0
_BREADTH_WIDE_THR = 0.60
_BREADTH_WEAK_THR = 0.40


def classify_stage(
    perf: SectorPerformance,
    rs: RelativeStrengthScore,
) -> SectorStage:
    """Determine lifecycle stage from current performance and RS metrics."""
    composite    = rs.composite
    momentum     = perf.momentum_score
    breadth      = perf.breadth_pct
    rel20        = perf.rel_return_20bar

    # LEADING: strong RS + strong momentum + wide breadth
    if composite >= _RS_LEADING_THR and momentum >= _MOM_STRONG_THR and breadth >= _BREADTH_WIDE_THR:
        return SectorStage.LEADING

    # OUTPERFORMING: strong positive relative return even if breadth is moderate
    if rel20 > 0.05 and composite >= _RS_LEADING_THR:
        return SectorStage.OUTPERFORMING

    # EMERGING: RS improving (composite 50-60) with accelerating momentum
    if 50.0 <= composite < _RS_LEADING_THR and momentum >= _MOM_STRONG_THR:
        return SectorStage.EMERGING

    # WEAKENING: previously high RS but falling momentum
    if composite >= 50.0 and momentum < _MOM_WEAK_THR:
        return SectorStage.WEAKENING

    # UNDERPERFORMING: strongly negative relative returns (takes priority over LAGGING)
    if rel20 < -0.05 and composite <= _RS_LAGGING_THR:
        return SectorStage.UNDERPERFORMING

    # LAGGING: low RS + weak momentum (no strong negative trend)
    if composite <= _RS_LAGGING_THR and momentum <= _MOM_WEAK_THR:
        return SectorStage.LAGGING

    # RECOVERING: RS improving from low but not yet above midpoint
    if composite < 50.0 and momentum >= _MOM_STRONG_THR:
        return SectorStage.RECOVERING

    # MATURE: above-average RS but slowing momentum
    if composite >= 50.0 and _MOM_WEAK_THR <= momentum < _MOM_STRONG_THR:
        return SectorStage.MATURE

    return SectorStage.UNKNOWN
