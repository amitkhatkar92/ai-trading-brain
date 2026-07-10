"""iios/investment/market/structure/structure_score.py
Aggregate individual confidence scores into an overall structure quality score.
"""
from __future__ import annotations

import logging

from iios.investment.market.structure.models import StructureQualityScore

logger = logging.getLogger(__name__)

# Weights must sum to 1.0
_W_SWING = 0.25
_W_TREND = 0.35
_W_ZONE = 0.20
_W_BREAKOUT = 0.10
_W_DATA = 0.10


class StructureScorer:
    """Compute a weighted overall StructureQualityScore."""

    def score(
        self,
        swing_conf: float,
        trend_conf: float,
        zone_conf: float,
        breakout_conf: float,
        data_quality: float,
        bar_count: int,
        valid_swing_count: int,
    ) -> StructureQualityScore:
        overall = (
            swing_conf * _W_SWING
            + trend_conf * _W_TREND
            + zone_conf * _W_ZONE
            + breakout_conf * _W_BREAKOUT
            + data_quality * _W_DATA
        )
        overall = max(0.0, min(100.0, overall))

        return StructureQualityScore(
            overall=overall,
            swing_confidence=swing_conf,
            trend_confidence=trend_conf,
            zone_confidence=zone_conf,
            breakout_confidence=breakout_conf,
            data_quality=data_quality,
            bar_count=bar_count,
            valid_swing_count=valid_swing_count,
        )
