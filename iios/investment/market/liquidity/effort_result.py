"""iios/investment/market/liquidity/effort_result.py
Wyckoff Effort vs Result analysis.
"""
from __future__ import annotations

import logging

from iios.investment.market.liquidity.models import (
    VolumeBar, EffortResultAnalysis, EffortResultType,
)

logger = logging.getLogger(__name__)


class EffortResultAnalyzer:
    """
    Wyckoff Effort vs Result analysis.
    Stateless — pure computation.
    """

    def analyze(
        self,
        vbar: VolumeBar,
        avg_volume: float,
        avg_range: float,
    ) -> EffortResultAnalysis:
        effort = min(1.0, vbar.volume / max(avg_volume * 3.0, 1.0))
        result = min(1.0, vbar.bar_range / max(avg_range * 3.0, 0.001))
        ratio = result / max(effort, 0.01)

        # Type classification in priority order.
        # ABSORPTION takes priority over CLIMAX when range is very small:
        # tiny range = price didn't move despite heavy volume = absorption, not climax.
        if effort > 0.70 and vbar.bar_range < avg_range * 0.50:
            er_type = EffortResultType.ABSORPTION
        elif effort > 0.85 and ratio < 0.50 and vbar.relative_volume > 2.5:
            er_type = EffortResultType.CLIMAX
        elif effort >= 0.60 and result < 0.30:
            er_type = EffortResultType.DIVERGENT
        elif effort >= 0.50 and result >= 0.50:
            er_type = EffortResultType.CONFIRMED
        elif effort < 0.30 and result < 0.20:
            er_type = EffortResultType.EXHAUSTION
        else:
            er_type = EffortResultType.NEUTRAL

        is_climax = er_type == EffortResultType.CLIMAX
        is_absorption = er_type == EffortResultType.ABSORPTION
        is_confirmed = er_type == EffortResultType.CONFIRMED
        is_divergent = er_type == EffortResultType.DIVERGENT

        absorption_strength = effort * (1.0 - ratio) if is_absorption else 0.0
        absorption_strength = max(0.0, min(1.0, absorption_strength))
        climax_score = effort if is_climax else 0.0

        initiative_buying = (
            vbar.is_up
            and vbar.relative_volume >= 1.2
            and vbar.close_position >= 0.70
        )
        initiative_selling = (
            not vbar.is_up
            and vbar.relative_volume >= 1.2
            and vbar.close_position <= 0.30
        )
        responsive_buying = (not vbar.is_up) and (vbar.relative_volume < 0.80)
        responsive_selling = vbar.is_up and (vbar.relative_volume < 0.80)

        return EffortResultAnalysis(
            effort=effort,
            result=result,
            ratio=ratio,
            effort_result_type=er_type,
            is_confirmed=is_confirmed,
            is_divergent=is_divergent,
            is_absorption=is_absorption,
            is_climax=is_climax,
            absorption_strength=absorption_strength,
            climax_score=climax_score,
            initiative_buying=initiative_buying,
            initiative_selling=initiative_selling,
            responsive_buying=responsive_buying,
            responsive_selling=responsive_selling,
        )
